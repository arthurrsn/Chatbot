import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Chave da API do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("A variável de ambiente GEMINI_API_KEY não está definida.")

# Modelos do Gemini
MODEL_EMBEDDING = "models/embedding-001" # Nome do modelo atualizado
MODEL_GENERATION = "gemini-2.5-flash"

# Configurações do Chatbot
SIMILARITY_THRESHOLD = 0.75
EXCEL_FILE_PATH = r"src/Base_Chatbot.xlsx"
SHEET_NAME = 0
PERGUNTA_COLUMN = 'Perguntas'
RESPOSTA_COLUMN = 'Respostas'