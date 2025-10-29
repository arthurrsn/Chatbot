import os
import time
import textwrap
import numpy as np
import pandas as pd
import google.generativeai as genai
import pickle  # Biblioteca para salvar/carregar o cache

from config import (
    GEMINI_API_KEY, MODEL_EMBEDDING, MODEL_GENERATION, SIMILARITY_THRESHOLD,
    EXCEL_FILE_PATH, SHEET_NAME, PERGUNTA_COLUMN, RESPOSTA_COLUMN
)

# Defina o caminho para o arquivo que guardará os embeddings
EMBEDDINGS_CACHE_PATH = "embeddings_cache.pkl"

class ChatbotModel:
    def __init__(self):
        """
        Inicializa o modelo, configura a API, carrega os dados e os embeddings
        (priorizando o cache para evitar chamadas desnecessárias à API).
        """
        self.df = None
        self.numero_vivenda = "5541999999999"  # Número para redirecionamento
        self.api_functional = True # Usaremos uma flag com nome mais claro
        self._configure_api()
        self._load_data_and_embeddings()

    def _configure_api(self):
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            print("Cliente Gemini inicializado com sucesso.")
        except Exception as e:
            print(f"ERRO ao inicializar o cliente Gemini: {e}")
            self.api_functional = False
            raise

    def _embed_fn(self, text):
        # Este método agora só é chamado quando o cache está sendo criado
        try:
            return genai.embed_content(
                model=MODEL_EMBEDDING,
                content=text,
                task_type="retrieval_document"
            )["embedding"]
        except Exception as e:
            # Se der erro durante a criação do cache, o processo deve parar
            print(f"ERRO CRÍTICO ao gerar embedding para o texto '{text}': {e}")
            self.api_functional = False
            # Lança a exceção para cima para interromper o .apply()
            raise e

    def _load_data_and_embeddings(self):
        """
        Carrega dados e embeddings. Se o cache de embeddings não existir,
        gera-os em lotes de 20 por minuto para respeitar os limites da API.
        """
        try:
            self.df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=SHEET_NAME)
            print(f"Dados lidos com sucesso do arquivo: {EXCEL_FILE_PATH}")
        except Exception as e:
            print(f"ERRO CRÍTICO ao ler o arquivo Excel: {e}")
            self.api_functional = False
            return

        if os.path.exists(EMBEDDINGS_CACHE_PATH):
            print(f"Carregando embeddings do cache: {EMBEDDINGS_CACHE_PATH}")
            with open(EMBEDDINGS_CACHE_PATH, 'rb') as f:
                self.df['Embeddings'] = pickle.load(f)
            print("Embeddings carregados com sucesso do cache.")
        else:
            print("Arquivo de cache não encontrado. Gerando novos embeddings...")
            try:
                embeddings_list = []
                total_rows = len(self.df)
                
                # Loop para processar as perguntas em lotes controlados
                for i, text in enumerate(self.df[PERGUNTA_COLUMN]):
                    print(f"Gerando embedding para a linha {i + 1}/{total_rows}...")
                    
                    embedding = self._embed_fn(text)
                    embeddings_list.append(embedding)
                    
                    # Verifica se um lote de 20 foi processado e se não é a última linha
                    if (i + 1) % 20 == 0 and (i + 1) < total_rows:
                        print(f"--- Lote de 20 processado. Pausando por 60 segundos para evitar limite de RPM... ---")
                        time.sleep(60)
                
                self.df['Embeddings'] = embeddings_list
                print("Embeddings gerados com sucesso.")
                
                with open(EMBEDDINGS_CACHE_PATH, 'wb') as f:
                    pickle.dump(self.df['Embeddings'], f)
                print(f"Embeddings salvos no cache: {EMBEDDINGS_CACHE_PATH}")

            except Exception as e:
                print(f"Não foi possível gerar os embeddings iniciais. O chatbot operará em modo fallback. Erro: {e}")
                self.api_functional = False
                self.df = None

    def get_answer(self, query: str) -> str:
        """
        Método público principal que orquestra a busca e geração da resposta.
        """
        # A verificação agora é mais robusta
        if not self.api_functional or self.df is None or 'Embeddings' not in self.df.columns:
            return "Olá! Tudo bem?\n\nNo momento, nosso sistema automatizado está fora do ar.\nPor favor, acesse o link abaixo para realizar o atendimento humanizado.\n\nhttps://wa.me/5541999999999?text=Olá%21%21+Quero+saber+mais+sobre+a+Vivenda+do+Mate%21"
        
        try:
            relevant_passage = self._find_best_passage(query)
            prompt = self._make_prompt(query, relevant_passage)
            final_answer = self._generate_response_with_backoff(prompt)
            return final_answer
        except Exception as e:
            print(f"Ocorreu um erro inesperado durante o processamento da resposta: {e}")
            # Retorna a mensagem de fallback também em caso de erros inesperados
            return "Desculpe, ocorreu um erro ao processar sua solicitação. Tente novamente mais tarde."

    def _find_best_passage(self, query):
        try:
            query_embedding = genai.embed_content(
                model=MODEL_EMBEDDING,
                content=query,
                task_type="retrieval_query"
            )["embedding"]

            dot_products = np.dot(np.stack(self.df['Embeddings']), query_embedding)
            max_score = np.max(dot_products)
            idx = np.argmax(dot_products)

            if max_score < SIMILARITY_THRESHOLD:
                return "SEM INFORMAÇÃO RELEVANTE"

            return self.df.iloc[idx][RESPOSTA_COLUMN]
        except Exception as e:
            print(f"Erro no processo de busca (retrieval): {e}")
            # Se a busca falhar (pode ser cota da query), também aciona o fallback
            self.api_functional = False
            return "SEM INFORMAÇÃO RELEVANTE"

    def _make_prompt(self, query, relevant_passage):
        if relevant_passage == "SEM INFORMAÇÃO RELEVANTE":
            return textwrap.dedent(f"""
                Você é um chatbot útil e honesto.
                O banco de dados não contém informações para responder à pergunta: '{query}'.
                Responda cordialmente que você não tem informações sobre isso.
                Redirecione o usuarío cordialmente dizendo que pede desculpas mas que o atendimento humano talvez sane as duvidas, entao redirecione para atendimento humano enviando o link a seguir:https://wa.me/{self.numero_vivenda}?text=Olá%21%21+Quero+saber+mais+sobre+a+Vivenda+do+Mate%21 
                ANSWER:
            """)
        else:
            escaped = relevant_passage.replace("'", "").replace('"', "").replace("\n", " ")
            return textwrap.dedent(f"""
                Você é um bot útil e amigável no WhatsApp. Responda à pergunta usando o texto da passagem de referência.
                Seja abrangente e use um tom amigável.
                QUESTION: '{query}'
                PASSAGE: '{escaped}'
                ANSWER:
            """)

    def _generate_response_with_backoff(self, prompt, max_retries=5):
        model_generation = genai.GenerativeModel(MODEL_GENERATION)
        for attempt in range(max_retries):
            try:
                response = model_generation.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"Erro na tentativa {attempt + 1}/{max_retries} de geração: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return "Desculpe, houve um erro na comunicação com a IA."
        return "Desculpe, houve um erro inesperado."