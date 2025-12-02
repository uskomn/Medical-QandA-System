from flask import Blueprint,request,jsonify
from datetime import datetime

chat_bp=Blueprint('chat',__name__)

@chat_bp.route('/answer_questions',methods=['POST'])
def chat():
    try:
        data=request.get_json()
        user_message=data.get('message','').strip()

        if not user_message:
            return jsonify({"error":"消息不能为空"}),400

        response="问答接口尚需开发，请等待"

        return jsonify({
            "response":response,
            "timestamp":datetime.utcnow().isoformat()
        })

    except Exception as e:
        return jsonify({"error":f"处理问答消息时出错{str(e)}"}),500
