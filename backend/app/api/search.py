from flask import Blueprint,jsonify

search_bp=Blueprint('search',__name__)

@search_bp.route('/knowledge_search',methods=['POST'])
def knowledge_search():
    return jsonify("返回的搜索内容"),400