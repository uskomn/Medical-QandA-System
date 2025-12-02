from flask import Blueprint,jsonify,request
from neo4j import GraphDatabase
import os

kg_bp=Blueprint('knowledge_graph',__name__)

# Neo4j连接配置
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'aqzdwsfneo')


class Neo4jKnowledgeGraph:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def get_knowledge_graph(self):
        """从 Neo4j 获取知识图谱数据"""
        with self.driver.session() as session:
            # 获取所有节点，适配新的实体类型
            nodes_result = session.run("""
                MATCH (n)
                RETURN n.id as id, 
                       n.name as name, 
                       labels(n)[0] as entityType,
                       CASE 
                        WHEN labels(n)[0] = '疾病' THEN n.严重程度
                        WHEN labels(n)[0] = '治疗' THEN n.紧急程度
                        WHEN labels(n)[0] = '检查' THEN n.检查目的
                        WHEN labels(n)[0] = '药物' THEN n.用药途径
                        WHEN labels(n)[0] = '生命体征' THEN n.正常范围
                        WHEN labels(n)[0] = '并发症' THEN n.发生率
                        ELSE null
                       END as properties
                ORDER BY id
            """)
            nodes = []
            for record in nodes_result:
                entity_type = record["entityType"]
                name = record["name"] or record["id"]

                # 映射实体类型到颜色组
                group_mapping = {
                    "疾病": "disease",
                    "治疗": "treatment",
                    "检查": "examination",
                    "药物": "medication",
                    "生命体征": "vital_signs",
                    "并发症": "complication"
                }

                nodes.append({
                    "id": record["id"],
                    "label": name,
                    "group": group_mapping.get(entity_type, "other"),
                    "type": entity_type,
                    "properties": record["properties"]
                })

            # 获取所有关系，适配新的关系类型
            links_result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN a.id as source, 
                       b.id as target, 
                       type(r) as relationshipType,
                       CASE 
                        WHEN type(r) = '需要治疗' THEN {时机: r.时机, 顺序: r.顺序, 条件: r.条件}
                        WHEN type(r) = '需要检查' THEN {频率: r.频率, 目的: r.目的}
                        WHEN type(r) = '使用药物' THEN {剂量: r.剂量, 给药方式: r.给药方式, 使用时机: r.使用时机, 注意事项: r.注意事项}
                        WHEN type(r) = '监测指标' THEN {监测频率: r.监测频率, 目标值: r.目标值}
                        WHEN type(r) = '引起并发症' THEN {发生率: r.发生率, 条件: r.条件}
                        ELSE {}
                       END as properties
                ORDER BY source
            """)
            links = []
            for record in links_result:
                relationship_type = record["relationshipType"]

                # 简化关系权重用于可视化
                weight = 1
                if "治疗" in relationship_type:
                    weight = 3
                elif "药物" in relationship_type:
                    weight = 2
                elif "检查" in relationship_type or "监测" in relationship_type:
                    weight = 1
                elif "并发症" in relationship_type:
                    weight = 2

                links.append({
                    "source": record["source"],
                    "target": record["target"],
                    "value": weight,
                    "relationshipType": relationship_type,
                    "properties": record["properties"]
                })

            return {"nodes": nodes, "links": links}

    def search_nodes(self, query):
        """搜索节点"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE toLower(n.name) CONTAINS toLower($query) 
                   OR toLower(n.症状描述) CONTAINS toLower($query)
                   OR toLower(n.注意事项) CONTAINS toLower($query)
                RETURN n.id as id, 
                       n.name as name, 
                       labels(n)[0] as entityType,
                       CASE 
                        WHEN labels(n)[0] = '疾病' THEN n.严重程度
                        WHEN labels(n)[0] = '治疗' THEN n.紧急程度
                        WHEN labels(n)[0] = '检查' THEN n.检查目的
                        WHEN labels(n)[0] = '药物' THEN n.用药途径
                        WHEN labels(n)[0] = '生命体征' THEN n.正常范围
                        WHEN labels(n)[0] = '并发症' THEN n.发生率
                        ELSE null
                       END as properties
                LIMIT 20
            """, query=query)

            nodes = []
            for record in result:
                entity_type = record["entityType"]
                name = record["name"] or record["id"]

                # 映射实体类型到颜色组
                group_mapping = {
                    "疾病": "disease",
                    "治疗": "treatment",
                    "检查": "examination",
                    "药物": "medication",
                    "生命体征": "vital_signs",
                    "并发症": "complication"
                }

                nodes.append({
                    "id": record["id"],
                    "label": name,
                    "group": group_mapping.get(entity_type, "other"),
                    "type": entity_type,
                    "properties": record["properties"]
                })

            return nodes

graph_db=Neo4jKnowledgeGraph(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

@kg_bp.route('/test_connection', methods=["GET"])
def test_connection():
    try:
        if graph_db:
            database_status="Neo4j数据库状态正常"
        else:
            database_status="Neo4j数据库状态异常"
        return jsonify({
            "status":"healthy",
            "message":"系统运行正常",
            "database_status":database_status
        })
    except Exception as e:
        print(f"出现异常{str(e)}")


@kg_bp.route('/get_kg',methods=['GET'])
def get_kg():
    try:
        graph_data=graph_db.get_knowledge_graph()
        return jsonify(graph_data)
    except Exception as e:
        print(f"获取知识图谱失败{str(e)}")

@kg_bp.route('/neo4j/status', methods=['GET'])
def neo4j_status():
    try:
        if graph_db:
            with graph_db.driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                return jsonify({
                    "status": "connected",
                    "uri": NEO4J_URI,
                    "message": "Neo4j连接正常"
                })
        else:
            return jsonify({
                "status": "disconnected",
                "message": "Neo4j未连接，使用模拟数据"
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Neo4j连接异常: {str(e)}"
        })