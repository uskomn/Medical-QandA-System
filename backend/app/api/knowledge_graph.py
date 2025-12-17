from flask import Blueprint,jsonify,request
from backend.app.utils.kg import Neo4jKnowledgeGraph
import os

kg_bp=Blueprint('knowledge_graph',__name__)


NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'aqzdwsfneo')

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