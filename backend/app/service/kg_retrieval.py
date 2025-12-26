import json
import re
from typing import List, Dict, Any, Tuple
from neo4j import GraphDatabase
import requests
import os

class KnowledgeGraphRetrieval:
    """知识图谱检索与推理系统"""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 deepseek_api_key: str = None):
        """初始化"""
        # 验证 Neo4j 连接
        try:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✓ Neo4j 连接成功")
        except Exception as e:
            print(f"✗ Neo4j 连接失败: {e}")
            raise

        # 验证 DeepSeek API
        self.deepseek_api_key = deepseek_api_key or os.getenv('DEEPSEEK_API_KEY')
        if not self.deepseek_api_key or self.deepseek_api_key == "your_api_key":
            print("⚠️  DeepSeek API key 未配置,将使用简化方法")
            self.use_llm = False
        else:
            self.use_llm = True
            print("✓ DeepSeek API key 已配置")

        self.deepseek_api_url = "https://api.deepseek.com/v1/chat/completions"

    def close(self):
        """关闭连接"""
        self.driver.close()

    # ========== 1. 图检索模块 ==========

    def retrieve_relevant_subgraph(self, query: str, max_depth: int = 2,
                                   top_k: int = 10) -> Dict[str, Any]:

        entities = self._extract_entities_from_query(query)
        matched_nodes = self._find_matching_nodes(entities)
        if not matched_nodes:
            print("✗ 未找到匹配节点\n")
            return {"nodes": [], "relationships": [], "paths": []}

        subgraph = self._expand_subgraph(matched_nodes, max_depth, top_k)
        print(f"✓ 扩展子图完成:")
        print(f"  - 节点数: {len(subgraph['nodes'])}")
        print(f"  - 关系数: {len(subgraph['relationships'])}")
        print(f"  - 路径数: {len(subgraph['paths'])}\n")

        return subgraph

    def _extract_entities_from_query(self, query: str) -> List[str]:
        """从查询中提取关键实体"""
        if self.use_llm:
            prompt = f"""从以下医疗问题中提取关键实体(疾病、治疗、药物、检查等)。

问题: {query}

只返回JSON数组,格式: ["实体1", "实体2", ...]
"""
            try:
                response = self._call_deepseek(prompt, max_tokens=200, temperature=0)
                response = re.sub(r'```json\s*', '', response.strip())
                response = re.sub(r'```\s*', '', response)
                entities = json.loads(response)
                if isinstance(entities, list) and entities:
                    return entities
            except Exception as e:
                print(f"⚠️  LLM 提取失败: {e}, 使用备用方法")

        # 备用方法
        keywords = []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    WHERE $query_text CONTAINS n.name
                    RETURN DISTINCT n.name as name
                    LIMIT 10
                """, query_text=query)
                keywords = [record['name'] for record in result]
        except Exception as e:
            print(f"⚠️  图谱匹配失败: {e}")

        return keywords if keywords else [query]

    def _find_matching_nodes(self, entities: List[str]) -> List[Dict]:
        """查找匹配的图谱节点"""
        matched = []
        with self.driver.session() as session:
            for entity in entities:
                result = session.run("""
                    MATCH (n)
                    WHERE n.name CONTAINS $entity
                    RETURN id(n) as node_id, 
                           labels(n)[0] as type,
                           n.name as name,
                           properties(n) as properties
                    LIMIT 5
                """, entity=entity)

                for record in result:
                    matched.append({
                        'id': record['node_id'],
                        'type': record['type'],
                        'name': record['name'],
                        'properties': dict(record['properties'])
                    })
        return matched

    def _expand_subgraph(self, seed_nodes: List[Dict], max_depth: int,
                         top_k: int) -> Dict[str, Any]:
        """扩展子图"""
        node_ids = [node['id'] for node in seed_nodes]

        with self.driver.session() as session:
            result = session.run(f"""
                MATCH path = (start)-[*1..{max_depth}]-(end)
                WHERE id(start) IN $node_ids
                WITH path, 
                     length(path) as path_length,
                     [rel in relationships(path) | type(rel)] as rel_types
                RETURN path,
                       [node in nodes(path) | {{
                           id: id(node),
                           type: labels(node)[0],
                           name: node.name,
                           properties: properties(node)
                       }}] as nodes,
                       [rel in relationships(path) | {{
                           type: type(rel),
                           properties: properties(rel)
                       }}] as relationships,
                       path_length,
                       rel_types
                ORDER BY path_length ASC
                LIMIT $top_k
            """, node_ids=node_ids, top_k=top_k)

            all_nodes = {}
            all_relationships = []
            all_paths = []

            for record in result:
                nodes = record['nodes']
                rels = record['relationships']

                for node in nodes:
                    node_id = node['id']
                    if node_id not in all_nodes:
                        all_nodes[node_id] = node

                for i, rel in enumerate(rels):
                    rel_data = {
                        'from': nodes[i]['id'],
                        'from_name': nodes[i]['name'],
                        'to': nodes[i + 1]['id'],
                        'to_name': nodes[i + 1]['name'],
                        'type': rel['type'],
                        'properties': rel['properties']
                    }
                    all_relationships.append(rel_data)

                path_desc = ' -> '.join([
                                            f"{nodes[i]['name']}[{rels[i]['type']}]"
                                            for i in range(len(rels))
                                        ] + [nodes[-1]['name']])

                all_paths.append({
                    'nodes': nodes,
                    'relationships': rels,
                    'description': path_desc,
                    'length': record['path_length']
                })

            return {
                'nodes': list(all_nodes.values()),
                'relationships': all_relationships,
                'paths': all_paths
            }

    # ========== 2. 基于子图的控制生成 ==========

    def controlled_generation_with_subgraph(self, query: str,
                                            use_consistency: bool = True,
                                            use_reasoning: bool = True) -> Dict[str, Any]:
        """
        基于子图的控制生成
        Args:
            query: 用户问题
            use_consistency: 是否使用自一致性检索
            use_reasoning: 是否使用多跳推理
        Returns:
            生成结果 (包含答案和验证)
        """
        print(f"\n{'=' * 60}")
        print(f"🎯 基于子图的控制生成")
        print(f"{'=' * 60}\n")

        # 1. 检索高一致性子图
        if use_consistency:
            consistency_result = self.self_consistency_retrieval(query, num_samples=3)
            subgraph = consistency_result['consistent_subgraph']
            consistency_info = f"""
一致性分析:
- 高一致性节点: {len(subgraph['nodes'])} 个
- 高一致性路径: {len(subgraph['paths'])} 个
- 平均一致性: {sum(n.get('consistency', 0) for n in subgraph['nodes']) / len(subgraph['nodes']) if subgraph['nodes'] else 0:.2%}
"""
        else:
            subgraph = self.retrieve_relevant_subgraph(query, max_depth=2, top_k=10)
            consistency_info = ""

        # 2. 多跳推理 (如果启用)
        reasoning_chains = []
        if use_reasoning:
            print("🧠 执行多跳推理...\n")
            entities = self._extract_entities_from_query(query)

            if len(entities) >= 2:
                for i in range(len(entities) - 1):
                    reasoning = self.multi_hop_reasoning(
                        query=f"{entities[i]} 和 {entities[i + 1]} 的关系",
                        max_hops=3
                    )
                    if reasoning and reasoning.get('paths'):
                        reasoning_chains.append({
                            'from': entities[i],
                            'to': entities[i + 1],
                            'path': reasoning['paths'][0]
                        })

            print(f"✓ 找到 {len(reasoning_chains)} 条推理链\n")

        # 3. 构建结构化知识
        structured_knowledge = self._format_subgraph_with_reasoning(
            subgraph, reasoning_chains
        )

        # 4. 硬约束生成
        print("📝 生成答案 (硬约束模式)...\n")
        answer, constrained_entities = self._generate_with_hard_constraints(
            query, structured_knowledge, consistency_info, subgraph
        )

        # 5. 验证
        validation = self.validate_generation_with_subgraph(answer, subgraph)

        return {
            'query': query,
            'answer': answer,
            'subgraph': subgraph,
            'reasoning_chains': reasoning_chains,
            'validation': validation,
            'constrained_entities': constrained_entities,
            'consistency_info': consistency_info
        }

    def _format_subgraph_with_reasoning(self, subgraph: Dict,
                                        reasoning_chains: List[Dict]) -> str:
        """格式化子图信息,融合推理链"""
        knowledge_parts = []

        # 1. 格式化节点信息
        knowledge_parts.append("【相关医疗实体】")

        nodes_by_type = {}
        for node in subgraph['nodes']:
            node_type = node['type']
            if node_type not in nodes_by_type:
                nodes_by_type[node_type] = []
            nodes_by_type[node_type].append(node)

        for node_type, nodes in nodes_by_type.items():
            knowledge_parts.append(f"\n{node_type}:")
            for node in nodes[:8]:
                props = node.get('properties', {})
                consistency = node.get('consistency', 0)

                # 过滤有效属性
                valid_props = {k: v for k, v in props.items()
                               if k not in ['id', 'name'] and v}

                if valid_props:
                    prop_str = ', '.join([f"{k}:{v}" for k, v in valid_props.items()])
                    if consistency > 0:
                        knowledge_parts.append(
                            f"  - {node['name']} ({prop_str}) [一致性:{consistency:.0%}]"
                        )
                    else:
                        knowledge_parts.append(f"  - {node['name']} ({prop_str})")
                else:
                    if consistency > 0:
                        knowledge_parts.append(
                            f"  - {node['name']} [一致性:{consistency:.0%}]"
                        )
                    else:
                        knowledge_parts.append(f"  - {node['name']}")

        # 2. 格式化关系路径
        knowledge_parts.append("\n【医疗知识关联】")

        sorted_paths = sorted(
            subgraph['paths'][:10],
            key=lambda p: p.get('consistency', 0),
            reverse=True
        )

        for path in sorted_paths:
            consistency = path.get('consistency', 0)
            if consistency > 0:
                knowledge_parts.append(
                    f"  {path['description']} [一致性:{consistency:.0%}]"
                )
            else:
                knowledge_parts.append(f"  {path['description']}")

        # 3. 融合推理链
        if reasoning_chains:
            knowledge_parts.append("\n【推理链】")
            for chain in reasoning_chains:
                path = chain['path']
                knowledge_parts.append(f"\n从 {chain['from']} 到 {chain['to']} 的推理:")

                for i in range(len(path['relations'])):
                    knowledge_parts.append(
                        f"  步骤{i + 1}: {path['nodes'][i]} "
                        f"--[{path['relations'][i]}]--> {path['nodes'][i + 1]}"
                    )

        return '\n'.join(knowledge_parts)

    def _generate_with_hard_constraints(self, query: str, structured_knowledge: str,
                                        consistency_info: str, subgraph: Dict) -> Tuple[str, List[str]]:
        """硬约束生成"""
        # 构建实体允许列表
        allowed_entities = [node['name'] for node in subgraph['nodes']]
        allowed_entities_str = ', '.join(allowed_entities)

        # 构建关系允许列表
        allowed_relations = list(set([
            f"{rel['from_name']} → {rel['type']} → {rel['to_name']}"
            for rel in subgraph['relationships']
        ]))
        allowed_relations_str = '\n  '.join(allowed_relations[:20])

        prompt = f"""你是专业的医疗知识问答助手。基于提供的知识图谱信息回答问题。

【硬约束规则 - 必须严格遵守】
1. ⚠️ 只能使用以下实体列表中的内容:
   {allowed_entities_str}

2. ⚠️ 只能使用以下已验证的关系:
   {allowed_relations_str}

3. ⚠️ 如果要提到某个实体,必须从允许列表中选择
4. ⚠️ 如果知识图谱信息不足,明确说明"图谱中暂无相关信息"
5. ⚠️ 包含实体的属性信息(剂量、时机、频率等)

{consistency_info}

【知识图谱信息】
{structured_knowledge}

【用户问题】
{query}

【回答格式要求】
请按照以下结构组织答案:

1. 【核心答案】(1-2句话总结)
2. 【详细说明】(分点展开,引用具体实体和关系)
3. 【重要提示】(如有特殊注意事项)

⚠️ 记住: 每个实体名称必须完全来自允许列表!

请回答:
"""

        # 生成答案
        if self.use_llm:
            try:
                response = self._call_deepseek(prompt, max_tokens=800, temperature=0.1)
            except Exception as e:
                print(f"⚠️  LLM 生成失败: {e}")
                response = self._generate_fallback_answer(query, subgraph)
        else:
            response = self._generate_fallback_answer(query, subgraph)

        # 后处理: 验证和过滤
        constrained_response, used_entities = self._enforce_entity_constraints(
            response, allowed_entities
        )

        return constrained_response, used_entities

    def _generate_fallback_answer(self, query: str, subgraph: Dict) -> str:
        """备用生成方法 (不使用LLM)"""
        answer_parts = []

        answer_parts.append("【基于知识图谱的回答】\n")

        if subgraph['nodes']:
            answer_parts.append("相关实体:")
            for node in subgraph['nodes'][:5]:
                answer_parts.append(f"  - {node['name']} ({node['type']})")

        if subgraph['paths']:
            answer_parts.append("\n相关知识:")
            for path in subgraph['paths'][:3]:
                answer_parts.append(f"  - {path['description']}")

        return '\n'.join(answer_parts)

    def _enforce_entity_constraints(self, text: str, allowed_entities: List[str]) -> Tuple[str, List[str]]:
        """强制实体约束 (后处理硬约束)"""
        used_entities = []

        # 找出文本中使用的实体
        for entity in allowed_entities:
            if entity in text:
                used_entities.append(entity)

        return text, used_entities

    # ========== 3. 自一致性检索 ==========

    def self_consistency_retrieval(self, query: str, num_samples: int = 3) -> Dict[str, Any]:
        """自一致性检索"""
        print(f"\n{'=' * 60}")
        print(f"🔄 自一致性检索 (采样{num_samples}次)")
        print(f"{'=' * 60}\n")

        all_subgraphs = []
        for i in range(num_samples):
            print(f"第 {i + 1}/{num_samples} 次检索...")
            subgraph = self.retrieve_relevant_subgraph(query, max_depth=2, top_k=8)
            all_subgraphs.append(subgraph)

        print(f"\n✓ 完成 {num_samples} 次检索\n")

        # 统计一致性
        node_counter = {}
        node_data = {}
        path_counter = {}
        rel_counter = {}
        rel_data = {}

        for subgraph in all_subgraphs:
            for node in subgraph['nodes']:
                key = (node['type'], node['name'])
                node_counter[key] = node_counter.get(key, 0) + 1
                if key not in node_data:
                    node_data[key] = node

            for rel in subgraph['relationships']:
                key = (rel['from_name'], rel['to_name'], rel['type'])
                rel_counter[key] = rel_counter.get(key, 0) + 1
                if key not in rel_data:
                    rel_data[key] = rel

            for path in subgraph['paths']:
                pattern = ' -> '.join([
                                          f"{path['nodes'][i]['name']}[{path['relationships'][i]['type']}]"
                                          for i in range(len(path['relationships']))
                                      ] + [path['nodes'][-1]['name']])
                path_counter[pattern] = path_counter.get(pattern, 0) + 1

        # 构建高一致性子图
        threshold = num_samples // 2 + 1

        consistent_nodes = []
        for (node_type, node_name), count in node_counter.items():
            if count >= threshold:
                node = node_data[(node_type, node_name)].copy()
                node['consistency'] = count / num_samples
                consistent_nodes.append(node)

        consistent_relationships = []
        for (from_name, to_name, rel_type), count in rel_counter.items():
            if count >= threshold:
                rel = rel_data[(from_name, to_name, rel_type)].copy()
                rel['consistency'] = count / num_samples
                consistent_relationships.append(rel)

        consistent_paths = []
        path_data = {}
        for subgraph in all_subgraphs:
            for path in subgraph['paths']:
                pattern = ' -> '.join([
                                          f"{path['nodes'][i]['name']}[{path['relationships'][i]['type']}]"
                                          for i in range(len(path['relationships']))
                                      ] + [path['nodes'][-1]['name']])
                if pattern not in path_data:
                    path_data[pattern] = path

        for pattern, count in path_counter.items():
            if count >= threshold and pattern in path_data:
                path = path_data[pattern].copy()
                path['consistency'] = count / num_samples
                consistent_paths.append(path)

        print(f"✓ 高一致性子图构建完成:")
        print(f"  - 一致性节点: {len(consistent_nodes)} 个")
        print(f"  - 一致性关系: {len(consistent_relationships)} 个")
        print(f"  - 一致性路径: {len(consistent_paths)} 个\n")

        consistent_subgraph = {
            'nodes': consistent_nodes,
            'relationships': consistent_relationships,
            'paths': consistent_paths
        }

        return {
            'query': query,
            'num_samples': num_samples,
            'consistent_subgraph': consistent_subgraph,
            'all_subgraphs': all_subgraphs,
            'statistics': {
                'node_counter': node_counter,
                'path_counter': path_counter
            }
        }

    # ========== 4. 多跳推理 ==========

    def multi_hop_reasoning(self, query: str, max_hops: int = 3) -> Dict[str, Any]:
        """
        多跳推理
        Args:
            query: 查询
            max_hops: 最大推理跳数
        Returns:
            推理链
        """
        print(f"\n{'=' * 60}")
        print(f"🧠 多跳推理 (最大{max_hops}跳)")
        print(f"{'=' * 60}\n")

        # 1. 提取起始实体和目标
        entities = self._extract_entities_from_query(query)
        if len(entities) < 2:
            print("✗ 需要至少2个实体进行多跳推理\n")
            return None

        start_entity = entities[0]
        end_entity = entities[-1]

        print(f"起始实体: {start_entity}")
        print(f"目标实体: {end_entity}\n")

        # 2. 查找推理路径
        reasoning_paths = self._find_reasoning_paths(start_entity, end_entity, max_hops)

        print(f"✓ 找到 {len(reasoning_paths)} 条推理路径\n")

        # 3. 评分和排序
        scored_paths = self._score_reasoning_paths(reasoning_paths)

        return {
            'start': start_entity,
            'end': end_entity,
            'paths': scored_paths
        }

    def _find_reasoning_paths(self, start: str, end: str, max_hops: int) -> List[Dict]:
        """查找推理路径"""
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH path = (start)-[*1..{max_hops}]-(end)
                WHERE start.name CONTAINS $start AND end.name CONTAINS $end
                WITH path,
                     [node in nodes(path) | node.name] as node_names,
                     [rel in relationships(path) | type(rel)] as rel_types,
                     length(path) as hops
                RETURN node_names, rel_types, hops
                ORDER BY hops ASC
                LIMIT 10
            """, start=start, end=end)

            paths = []
            for record in result:
                paths.append({
                    'nodes': record['node_names'],
                    'relations': record['rel_types'],
                    'hops': record['hops']
                })

            return paths

    def _score_reasoning_paths(self, paths: List[Dict]) -> List[Dict]:
        """评分推理路径"""
        for path in paths:
            # 评分因素:
            # 1. 路径长度(越短越好)
            length_score = 1.0 / (path['hops'] + 1)

            # 2. 关系类型重要性
            important_rels = ['需要治疗', '使用药物', '需要检查']
            rel_score = sum(1 for r in path['relations'] if r in important_rels) / len(path['relations']) if path[
                'relations'] else 0

            # 综合评分
            path['score'] = 0.6 * length_score + 0.4 * rel_score

        # 排序
        paths.sort(key=lambda x: x['score'], reverse=True)

        return paths

    # ========== 5. 子图验证 ==========

    def validate_generation_with_subgraph(self, generated_answer: str,
                                          subgraph: Dict) -> Dict[str, Any]:
        """
        验证生成内容是否与子图一致
        Args:
            generated_answer: 生成的答案
            subgraph: 参考子图
        Returns:
            验证结果
        """
        print(f"\n{'=' * 60}")
        print(f"✅ 验证生成内容")
        print(f"{'=' * 60}\n")

        # 1. 提取答案中的实体
        answer_entities = self._extract_entities_from_text(generated_answer)

        # 2. 检查实体是否在子图中
        subgraph_entity_names = {node['name'] for node in subgraph['nodes']}

        valid_entities = [e for e in answer_entities if e in subgraph_entity_names]
        invalid_entities = [e for e in answer_entities if e not in subgraph_entity_names]

        # 3. 检查关系陈述
        relation_claims = self._extract_relation_claims(generated_answer)
        verified_claims = self._verify_claims_with_subgraph(relation_claims, subgraph)

        # 4. 计算一致性分数
        entity_consistency = len(valid_entities) / len(answer_entities) if answer_entities else 0
        claim_consistency = sum(1 for c in verified_claims if c['verified']) / len(
            verified_claims) if verified_claims else 0

        overall_score = 0.5 * entity_consistency + 0.5 * claim_consistency

        print(f"验证结果:")
        print(f"  - 实体一致性: {entity_consistency:.2%}")
        print(f"  - 关系一致性: {claim_consistency:.2%}")
        print(f"  - 总体一致性: {overall_score:.2%}\n")

        return {
            'overall_score': overall_score,
            'entity_consistency': entity_consistency,
            'claim_consistency': claim_consistency,
            'valid_entities': valid_entities,
            'invalid_entities': invalid_entities,
            'verified_claims': verified_claims
        }

    def _extract_entities_from_text(self, text: str) -> List[str]:
        """从文本中提取实体"""
        entities = []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    WHERE $text_content CONTAINS n.name
                    RETURN DISTINCT n.name as name
                """, text_content=text)
                entities = [record['name'] for record in result]
        except Exception as e:
            print(f"⚠️  提取实体失败: {e}")

        return entities

    def _extract_relation_claims(self, text: str) -> List[str]:
        """提取关系陈述"""
        # 简化版本:提取句子
        sentences = [s.strip() for s in text.split('。') if s.strip()]
        return sentences

    def _verify_claims_with_subgraph(self, claims: List[str],
                                     subgraph: Dict) -> List[Dict]:
        """验证陈述与子图的一致性"""
        verified = []

        for claim in claims:
            # 检查陈述中是否包含子图的路径
            is_verified = False
            supporting_path = None

            for path in subgraph['paths']:
                # 简单检查:如果陈述包含路径中的关键实体
                path_entities = [node['name'] for node in path['nodes']]
                if any(entity in claim for entity in path_entities[:2]):
                    is_verified = True
                    supporting_path = path['description']
                    break

            verified.append({
                'claim': claim,
                'verified': is_verified,
                'supporting_path': supporting_path
            })

        return verified

    # ========== 辅助方法 ==========

    def _call_deepseek(self, prompt: str, max_tokens: int = 1000,
                       temperature: float = 0) -> str:
        """调用DeepSeek API"""
        if not self.use_llm:
            raise Exception("DeepSeek API 未配置")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是专业的医疗知识助手。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        response = requests.post(self.deepseek_api_url, headers=headers,
                                 json=payload, timeout=60)
        response.raise_for_status()

        response_data = response.json()
        return response_data['choices'][0]['message']['content']