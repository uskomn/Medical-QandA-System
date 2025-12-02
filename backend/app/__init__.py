from flask import Flask
from flask_cors import CORS
from backend.app.api.chat import chat_bp
from backend.app.api.knowledge_graph import kg_bp

def create_app():
    app=Flask(__name__)
    CORS(app,supports_credentials=True)

    app.register_blueprint(chat_bp,url_prefix='/chat')
    app.register_blueprint(kg_bp,url_prefix='/knowledge_graph')
    return app