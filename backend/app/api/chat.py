from flask import Blueprint,request,jsonify
from backend.app.service.kg_retrieval import KnowledgeGraphRetrieval
from datetime import datetime
import os

chat_bp=Blueprint('chat',__name__)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "aqzdwsfneo"
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY') or "sk-8cbf10f456ae40aba1be330eaa3c2397"

retrieval=KnowledgeGraphRetrieval(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,DEEPSEEK_API_KEY)

@chat_bp.route('/answer_questions',methods=['POST'])
def chat():
    try:
        data=request.get_json()
        user_message=data.get('message','').strip()

        if not user_message:
            return jsonify({"error":"消息不能为空"}),400

        response=retrieval.controlled_generation_with_subgraph(user_message,use_consistency=True,use_reasoning=True)
        return jsonify({
            "response":response['answer'],
            "timestamp":datetime.utcnow().isoformat()
        })

    except Exception as e:
        return jsonify({"error":f"处理问答消息时出错{str(e)}"}),500
