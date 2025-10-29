from flask import Blueprint, request, jsonify
from models.chatbot_model import ChatbotModel
from utils.evolutionAPI import EvolutionAPI


ID_CONTATO_DONO = '5541999999'
IDS_A_IGNORAR = [
    ID_CONTATO_DONO,
    # Adicione outros IDs que o bot deve ignorar, se houver
]

# Cria um "Blueprint", que é um componente de app Flask modular
chatbot_bp = Blueprint('chatbot', __name__)


# Instancia o Model e a API FORA da função da rota.
# Isso garante que a base de dados seja carregada e os embeddings gerados APENAS UMA VEZ
# quando a aplicação inicia, e não a cada nova mensagem.
chatbot_model = ChatbotModel()
evolution_api = EvolutionAPI()

@chatbot_bp.route('/webhook', methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Requisição sem corpo JSON"}), 400

        # 1. Extração e Validação dos Dados da Requisição
        instance = data.get("instance")
        apikey = data.get("apikey")
        sender_number = data.get("data", {}).get("key", {}).get("remoteJid", "").split("@")[0]

        # --- VERIFICAÇÃO PARA IGNORAR O DONO ---
        if sender_number in IDS_A_IGNORAR:
            print(f"Mensagem recebida do ID do dono ({sender_number}). Ignorando resposta.")
            return jsonify({"status": "remetente ignorado"}), 200
        
        # Tratamento seguro para extrair a mensagem
        message_data = data.get("data", {}).get("message", {})
        message = message_data.get("conversation") if message_data else None

        if not all([instance, apikey, sender_number]):
            return jsonify({"error": "Dados essenciais (instance, apikey, sender_number) faltando"}), 400

        # 2. Lógica para lidar com mensagens de tipo diferente de texto
        if not message:
            response_text = "No momento, nosso sistema aceita apenas mensagens de texto."
            evolution_api.enviar_mensagem(
                message=response_text,
                instance=instance,
                instance_key=apikey,
                sender_number=sender_number
            )
            return jsonify({"status": "resposta enviada", "content": response_text}), 200

        # 3. Chamar o Model para obter a resposta
        final_answer = chatbot_model.get_answer(message)

        # 4. Enviar a resposta via serviço externo
        evolution_api.enviar_mensagem(
            message=final_answer,
            instance=instance,
            instance_key=apikey,
            sender_number=sender_number
        )

        # 5. Retornar a resposta HTTP (a "View" da nossa API)
        return jsonify({"status": "sucesso", "response": final_answer}), 200

    except Exception as e:
        print(f"ERRO GERAL NO WEBHOOK: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor"}), 500