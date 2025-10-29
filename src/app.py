from flask import Flask
from controllers.chatbot_controller import chatbot_bp

# Cria a instância da aplicação Flask
app = Flask(__name__)

# Registra o Blueprint do controller na aplicação
# Todas as rotas definidas em 'chatbot_bp' (como /webhook) estarão ativas
app.register_blueprint(chatbot_bp)

if __name__ == '__main__':
    # Roda a aplicação na porta 5000 em modo de desenvolvimento
    app.run(port=5000, debug=True)