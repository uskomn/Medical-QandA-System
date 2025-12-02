import json
import re
from neo4j import GraphDatabase
from typing import Dict, List, Any
from model.utils.readDocx import readDocx
import requests
import os


class MedicalKGBuilder:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 deepseek_api_key: str = None):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.deepseek_api_key = deepseek_api_key or os.getenv('DEEPSEEK_API_KEY')
        self.deepseek_api_url = "https://api.deepseek.com/v1/chat/completions"

    def close(self):
        """关闭数据库连接"""
        self.driver.close()

    def extract_knowledge_from_text(self, text: str, chunk_size: int = 1500) -> Dict[str, Any]:
        """
        使用DeepSeek提取文本中的知识图谱结构(分批处理+重叠)
        Args:
            text: 医疗文档文本
            chunk_size: 每批处理的文本长度
        Returns:
            包含entities和relationships的字典
        """
        print("正在使用DeepSeek分析文档(分批处理+重叠)...")

        # 使用重叠窗口分割文本,避免信息丢失
        overlap = 300  # 重叠300字符
        text_chunks = []

        i = 0
        while i < len(text):
            chunk_end = min(i + chunk_size, len(text))
            chunk = text[i:chunk_end].strip()

            if chunk:
                text_chunks.append(chunk)

            # 下一个块从当前块的后overlap位置开始
            i += (chunk_size - overlap)

        print(f"文档已分成 {len(text_chunks)} 批(每批重叠{overlap}字符)")

        all_entities = []
        all_relationships = []
        entity_id_counter = {}

        # 逐批处理
        for idx, chunk in enumerate(text_chunks):
            print(f"\n处理第 {idx + 1}/{len(text_chunks)} 批 (长度: {len(chunk)} 字符)...")

            try:
                kg_chunk = self._extract_from_chunk(chunk, idx)

                # 重新分配ID以确保全局唯一
                kg_chunk = self._reassign_ids(kg_chunk, entity_id_counter)

                all_entities.extend(kg_chunk['entities'])
                all_relationships.extend(kg_chunk['relationships'])

                print(
                    f"✓ 第 {idx + 1} 批完成: {len(kg_chunk['entities'])} 个实体, {len(kg_chunk['relationships'])} 个关系")

            except Exception as e:
                print(f"✗ 第 {idx + 1} 批处理失败: {e}")
                print("跳过此批次,继续处理...")
                continue

        # 合并去重
        final_kg = self._merge_and_deduplicate({
            'entities': all_entities,
            'relationships': all_relationships
        })

        print(f"\n{'=' * 50}")
        print(f"✓ 全部处理完成!")
        print(f"  总实体数: {len(final_kg['entities'])}")
        print(f"  总关系数: {len(final_kg['relationships'])}")
        print(f"  重叠去重率: {len(all_entities) - len(final_kg['entities'])} 个重复实体已合并")
        print(f"{'=' * 50}\n")

        return final_kg

    def _extract_from_chunk(self, text: str, batch_idx: int) -> Dict[str, Any]:
        """
        从单个文本块提取知识(使用分步提取避免超长输出)
        Args:
            text: 文本块
            batch_idx: 批次索引
        Returns:
            包含entities和relationships的字典
        """
        # 方案: 先提取实体,再提取关系(分两次调用)
        print(f"  [1/2] 提取实体...")
        entities = self._extract_entities_only(text)

        if not entities:
            return {'entities': [], 'relationships': []}

        print(f"  [2/2] 提取关系...")
        relationships = self._extract_relationships_only(text, entities)

        return {
            'entities': entities,
            'relationships': relationships
        }

    def _extract_entities_only(self, text: str) -> List[Dict]:
        """只提取实体(包含属性)"""
        text_sample = text[:1200] if len(text) > 1200 else text

        prompt = f"""从医疗文档中提取关键实体及其属性。

实体类型与属性要求:
- 疾病: 严重程度(危重/急症/一般)、所属系统(循环/呼吸/消化等)、症状描述
- 治疗: 紧急程度(立即/尽快/常规)、操作类型(手术/物理/药物)、注意事项
- 检查: 检查目的、正常范围、异常指标
- 药物: 用药途径(静脉/口服/肌注)、剂量、使用时机
- 生命体征: 正常范围、异常阈值、监测频率
- 并发症: 发生率、危险因素、预防措施

严格规则:
1. 每种类型最多5个,总共不超过25个
2. properties必须包含至少1个有意义的属性
3. 如果文档中没有属性信息,properties可为空对象
4. 直接返回JSON数组

格式示例:
[
  {{"id":"d1","type":"疾病","name":"心脏骤停","properties":{{"严重程度":"危重","所属系统":"循环系统"}}}},
  {{"id":"t1","type":"治疗","name":"心肺复苏","properties":{{"紧急程度":"立即","操作类型":"手法"}}}},
  {{"id":"m1","type":"药物","name":"肾上腺素","properties":{{"用药途径":"静脉注射","剂量":"1mg"}}}},
  {{"id":"v1","type":"生命体征","name":"心率","properties":{{"正常范围":"60-100次/分","异常阈值":"<50或>130次/分"}}}}
]

文档: {text_sample}
"""

        try:
            response = self._call_deepseek(prompt, max_tokens=1200)
            response_text = self._clean_json_response(response)

            # 提取JSON数组
            if not response_text.startswith('['):
                match = re.search(r'"entities"\s*:\s*(\[.*?\])', response_text, re.DOTALL)
                if match:
                    response_text = match.group(1)
                else:
                    match = re.search(r'(\[.*\])', response_text, re.DOTALL)
                    if match:
                        response_text = match.group(1)

            entities = json.loads(response_text)

            if isinstance(entities, dict) and 'entities' in entities:
                entities = entities['entities']

            # 确保properties字段存在
            for e in entities:
                if 'properties' not in e:
                    e['properties'] = {}

            print(f"      提取到 {len(entities)} 个实体")

            # 统计有属性的实体数量
            with_props = sum(1 for e in entities if e.get('properties'))
            if with_props > 0:
                print(f"      其中 {with_props} 个包含属性信息")

            return entities[:35]

        except Exception as e:
            print(f"      实体提取失败: {e}")
            return []

    def _extract_relationships_only(self, text: str, entities: List[Dict]) -> List[Dict]:
        """只提取关系(包含关系属性)"""
        entity_ids = [e['id'] for e in entities[:25]]
        entity_list = ', '.join([f"{e['id']}({e['name']})" for e in entities[:25]])

        text_sample = text[:1000] if len(text) > 1000 else text

        prompt = f"""基于已提取的实体,找出它们之间的关系及关系属性。

实体列表: {entity_list}

关系类型与属性:
- 需要治疗: 时机(立即/尽快/必要时)、顺序(首选/备选)、条件(如症状严重时)
- 需要检查: 频率(持续/定期/必要时)、目的(确诊/监测/评估)
- 使用药物: 剂量、给药方式、使用时机、注意事项
- 监测指标: 监测频率(持续/每小时/定期)、目标值
- 引起并发症: 发生率(常见/少见)、条件(如未及时治疗)

严格规则:
1. 最多40个关系
2. properties可包含关系的详细信息,也可为空
3. from和to必须在实体列表中
4. 直接返回JSON数组

格式示例:
[
  {{"from":"d1","to":"t1","type":"需要治疗","properties":{{"时机":"立即","优先级":"最高"}}}},
  {{"from":"d1","to":"m1","type":"使用药物","properties":{{"剂量":"1mg","途径":"静脉"}}}},
  {{"from":"d2","to":"v1","type":"监测指标","properties":{{"频率":"持续监测"}}}}
]

文档: {text_sample}
"""

        try:
            response = self._call_deepseek(prompt, max_tokens=1800)
            response_text = self._clean_json_response(response)

            # 提取JSON数组
            if not response_text.startswith('['):
                match = re.search(r'"relationships"\s*:\s*(\[.*?\])', response_text, re.DOTALL)
                if match:
                    response_text = match.group(1)
                else:
                    match = re.search(r'(\[.*\])', response_text, re.DOTALL)
                    if match:
                        response_text = match.group(1)

            relationships = json.loads(response_text)

            if isinstance(relationships, dict) and 'relationships' in relationships:
                relationships = relationships['relationships']

            # 确保properties并验证ID存在
            valid_rels = []
            for r in relationships:
                if 'properties' not in r:
                    r['properties'] = {}
                if r.get('from') in entity_ids and r.get('to') in entity_ids:
                    valid_rels.append(r)

            print(f"      提取到 {len(valid_rels)} 个有效关系")

            # 统计有属性的关系数量
            with_props = sum(1 for r in valid_rels if r.get('properties'))
            if with_props > 0:
                print(f"      其中 {with_props} 个包含属性信息")

            return valid_rels[:60]

        except Exception as e:
            print(f"      关系提取失败: {e}")
            return []

    def _call_deepseek(self, prompt: str, max_tokens: int = 1000) -> str:
        """调用DeepSeek API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是JSON数据提取专家。只返回JSON数组,不要其他内容。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0,
            "max_tokens": max_tokens
        }

        response = requests.post(self.deepseek_api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        response_data = response.json()
        return response_data['choices'][0]['message']['content']

    def _fix_truncated_json(self, text: str) -> str:
        """修复被截断的JSON"""
        text = text.strip()

        # 如果JSON不完整,尝试补全
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')

        # 补全缺失的括号
        if open_braces > close_braces:
            text += '}' * (open_braces - close_braces)

        if open_brackets > close_brackets:
            text += ']' * (open_brackets - close_brackets)

        # 移除末尾不完整的行
        lines = text.split('\n')

        # 从后往前找到完整的结构
        for i in range(len(lines) - 1, -1, -1):
            test_text = '\n'.join(lines[:i + 1])

            # 尝试补全并解析
            test_open_braces = test_text.count('{')
            test_close_braces = test_text.count('}')
            test_open_brackets = test_text.count('[')
            test_close_brackets = test_text.count(']')

            if test_open_braces > test_close_braces:
                test_text += '}' * (test_open_braces - test_close_braces)
            if test_open_brackets > test_close_brackets:
                test_text += ']' * (test_open_brackets - test_close_brackets)

            try:
                json.loads(test_text)
                return test_text
            except:
                continue

        return text

    def _reassign_ids(self, kg_data: Dict, id_counter: Dict) -> Dict:
        """
        重新分配ID以确保全局唯一
        Args:
            kg_data: 知识图谱数据
            id_counter: ID计数器
        Returns:
            重新分配ID后的数据
        """
        id_mapping = {}  # 旧ID -> 新ID的映射

        for entity in kg_data['entities']:
            entity_type = entity['type']
            old_id = entity['id']

            # 根据类型生成前缀(支持中文类型)
            prefix_map = {
                '疾病': 'd',
                '治疗': 't',
                '检查': 'e',
                '药物': 'm',
                '生命体征': 'v',
                '并发症': 'c',
                # 兼容英文
                'Disease': 'd',
                'Treatment': 't',
                'Examination': 'e',
                'Medication': 'm',
                'VitalSign': 'v',
                'Complication': 'c'
            }
            prefix = prefix_map.get(entity_type, 'n')

            # 生成新ID
            if prefix not in id_counter:
                id_counter[prefix] = 0
            id_counter[prefix] += 1
            new_id = f"{prefix}{id_counter[prefix]}"

            id_mapping[old_id] = new_id
            entity['id'] = new_id

        # 更新关系中的ID引用
        for rel in kg_data['relationships']:
            if rel['from'] in id_mapping:
                rel['from'] = id_mapping[rel['from']]
            if rel['to'] in id_mapping:
                rel['to'] = id_mapping[rel['to']]

        return kg_data

    def _merge_and_deduplicate(self, kg_data: Dict) -> Dict:
        """
        合并并去重实体和关系
        Args:
            kg_data: 知识图谱数据
        Returns:
            去重后的数据
        """
        print("\n正在合并和去重...")

        # 去重实体 (基于name和type)
        unique_entities = {}
        entity_id_map = {}  # 旧ID -> 新ID的映射

        for entity in kg_data['entities']:
            key = (entity['type'], entity['name'])
            if key not in unique_entities:
                unique_entities[key] = entity
                entity_id_map[entity['id']] = entity['id']
            else:
                # 记录ID映射关系
                entity_id_map[entity['id']] = unique_entities[key]['id']

        # 更新关系中的ID引用
        for rel in kg_data['relationships']:
            if rel['from'] in entity_id_map:
                rel['from'] = entity_id_map[rel['from']]
            if rel['to'] in entity_id_map:
                rel['to'] = entity_id_map[rel['to']]

        # 去重关系
        unique_relationships = []
        seen_rels = set()

        for rel in kg_data['relationships']:
            # 确保引用的实体存在
            from_exists = any(e['id'] == rel['from'] for e in unique_entities.values())
            to_exists = any(e['id'] == rel['to'] for e in unique_entities.values())

            if not (from_exists and to_exists):
                continue

            rel_key = (rel['from'], rel['to'], rel['type'])
            if rel_key not in seen_rels:
                seen_rels.add(rel_key)
                unique_relationships.append(rel)

        result = {
            'entities': list(unique_entities.values()),
            'relationships': unique_relationships
        }

        print(f"去重完成: {len(result['entities'])} 个唯一实体, {len(result['relationships'])} 个唯一关系")

        return result

    def _clean_json_response(self, text: str) -> str:
        """清理JSON响应"""
        # 移除markdown代码块标记 (包括各种变体)
        text = re.sub(r'```json\s*\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*\n?', '', text)

        # 移除BOM
        if text.startswith('\ufeff'):
            text = text[1:]

        # 去除首尾空白
        text = text.strip()

        # 如果文本以非JSON字符开始,尝试找到第一个{
        if text and text[0] not in ('{', '['):
            first_brace = text.find('{')
            if first_brace != -1:
                text = text[first_brace:]

        # 如果文本以非JSON字符结束,尝试找到最后一个}
        if text and text[-1] not in ('}', ']'):
            last_brace = text.rfind('}')
            if last_brace != -1:
                text = text[:last_brace + 1]

        return text

    def _ensure_unique_ids(self, kg_data: Dict) -> Dict:
        """确保实体ID唯一(保留用于向后兼容)"""
        return kg_data

    def create_constraints(self):
        """创建Neo4j约束和索引(使用中文标签)"""
        print("创建数据库约束和索引...")

        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:疾病) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:治疗) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:检查) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:药物) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:生命体征) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:并发症) REQUIRE c.id IS UNIQUE"
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"约束创建警告: {e}")

    def create_entities(self, entities: List[Dict]):
        """创建实体节点(包含所有属性)"""
        print(f"创建{len(entities)}个实体节点...")

        with self.driver.session() as session:
            for entity in entities:
                entity_type = entity['type']
                entity_id = entity['id']
                entity_name = entity['name']
                properties = entity.get('properties', {})

                # 构建属性设置语句 (正确的Cypher语法)
                # SET n.prop1 = $prop1, n.prop2 = $prop2
                prop_assignments = []
                params = {
                    'id': entity_id,
                    'name': entity_name
                }

                # 添加所有properties到参数中
                for key, value in properties.items():
                    # 清理属性名(移除特殊字符,避免语法错误)
                    safe_key = key.replace(' ', '_').replace('-', '_').replace('/', '_')
                    prop_assignments.append(f"n.`{safe_key}` = ${safe_key}")
                    params[safe_key] = value

                # 构建SET子句
                if prop_assignments:
                    set_clause = f"SET n.name = $name, {', '.join(prop_assignments)}"
                else:
                    set_clause = "SET n.name = $name"

                # 使用反引号包裹标签,支持中文
                cypher = f"""
                MERGE (n:`{entity_type}` {{id: $id}})
                {set_clause}
                """

                try:
                    session.run(cypher, params)
                except Exception as e:
                    print(f"  警告: 创建实体 {entity_name} 时出错: {e}")
                    # 如果失败,尝试只创建基本信息
                    cypher_fallback = f"""
                    MERGE (n:`{entity_type}` {{id: $id}})
                    SET n.name = $name
                    """
                    session.run(cypher_fallback, {'id': entity_id, 'name': entity_name})

        print("实体创建完成")

    def create_relationships(self, relationships: List[Dict]):
        """创建关系(包含所有属性)"""
        print(f"创建{len(relationships)}个关系...")

        with self.driver.session() as session:
            for rel in relationships:
                from_id = rel['from']
                to_id = rel['to']
                rel_type = rel['type']
                properties = rel.get('properties', {})

                # 构建关系属性
                params = {
                    'from_id': from_id,
                    'to_id': to_id
                }

                # 添加所有properties到参数中
                prop_assignments = []
                for key, value in properties.items():
                    # 清理属性名
                    safe_key = key.replace(' ', '_').replace('-', '_').replace('/', '_')
                    prop_assignments.append(f"r.`{safe_key}` = ${safe_key}")
                    params[safe_key] = value

                # 构建SET子句
                if prop_assignments:
                    set_clause = f"SET {', '.join(prop_assignments)}"
                else:
                    set_clause = ""

                # 使用反引号包裹关系类型,支持中文
                cypher = f"""
                MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
                MERGE (a)-[r:`{rel_type}`]->(b)
                {set_clause}
                """

                try:
                    session.run(cypher, params)
                except Exception as e:
                    print(f"  警告: 创建关系 {from_id} -> {to_id} 时出错: {e}")

        print("关系创建完成")

    def build_knowledge_graph(self, document_text: str, chunk_size: int = 3000):
        """
        构建完整的知识图谱(分批处理)
        Args:
            document_text: 医疗文档文本
            chunk_size: 每批处理的文本长度(默认3000字符)
        """
        print("=" * 50)
        print("开始构建知识图谱(分批处理模式)")
        print("=" * 50)

        # 1. 提取知识(分批)
        kg_data = self.extract_knowledge_from_text(document_text, chunk_size)

        # 2. 创建约束
        self.create_constraints()

        # 3. 创建实体
        self.create_entities(kg_data['entities'])

        # 4. 创建关系
        self.create_relationships(kg_data['relationships'])

        print("=" * 50)
        print("知识图谱构建完成!")
        print("=" * 50)

        return kg_data

    def query_graph(self, cypher: str) -> List[Dict]:
        """
        查询图谱
        Args:
            cypher: Cypher查询语句
        Returns:
            查询结果列表
        """
        with self.driver.session() as session:
            result = session.run(cypher)
            return [record.data() for record in result]

    def get_statistics(self) -> Dict:
        """获取图谱统计信息(支持中文标签)"""
        stats = {}

        with self.driver.session() as session:
            # 统计各类型节点数量(支持中英文)
            node_types = ['疾病', '治疗', '检查', '药物', '生命体征', '并发症']

            for node_type in node_types:
                try:
                    result = session.run(f"MATCH (n:`{node_type}`) RETURN count(n) as count")
                    count = result.single()
                    if count:
                        stats[node_type] = count['count']
                except:
                    stats[node_type] = 0

            # 统计关系数量
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            stats['总关系数'] = result.single()['count']

            # 统计总节点数
            result = session.run("MATCH (n) RETURN count(n) as count")
            stats['总节点数'] = result.single()['count']

        return stats

def main():
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "aqzdwsfneo"  # 请修改为你的密码

    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY') or "sk-8cbf10f456ae40aba1be330eaa3c2397"

    CHUNK_SIZE = 1500

    base_dir = os.path.dirname(os.path.abspath(__file__))
    text_dir = os.path.join(base_dir, "words/需要紧急救治的急危重伤病标准.docx")

    document_text = readDocx(text_dir)

    builder = MedicalKGBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, DEEPSEEK_API_KEY)

    try:
        kg_data = builder.build_knowledge_graph(document_text, chunk_size=CHUNK_SIZE)

        with open('knowledge_graph.json', 'w', encoding='utf-8') as f:
            json.dump(kg_data, f, ensure_ascii=False, indent=2)
        print("\n知识图谱数据已保存到 knowledge_graph.json")

        print("\n图谱统计信息:")
        stats = builder.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")


    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        builder.close()
        print("\n数据库连接已关闭")


if __name__ == "__main__":
    main()