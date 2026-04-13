import os
from google import genai
import feedparser
import time
from datetime import datetime
import pytz

# Configuração simples
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)
fuso = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

# Usaremos apenas um feed para testar rápido
FEED_URL = "https://ge.globo.com/rss/ge/"

def atualizar():
    print("Iniciando teste de conexão...")
    feed = feedparser.parse(FEED_URL)
    
    if not feed.entries:
        print("Erro: Não foi possível ler o feed RSS.")
        return

    entry = feed.entries[0]
    print(f"Notícia encontrada: {entry.title}")

    # Teste da IA
    prompt = f"Resuma em 2 parágrafos: {entry.title}. Resumo original: {entry.summary}"
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        texto_ia = response.text
        print("IA respondeu com sucesso!")
    except Exception as e:
        print(f"Erro na IA: {e}")
        texto_ia = "Erro ao processar com IA."

    # HTML Simplificado ao extremo
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"><title>Teste</title></head>
    <body style="font-family: sans-serif; padding: 50px; background: #f4f4f4;">
        <h1>Portal IA News - Teste de Emergência</h1>
        <p>Atualizado em: {agora}</p>
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2>{entry.title}</h2>
            <p>{texto_ia}</p>
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Arquivo index.html escrito com sucesso!")

if __name__ == "__main__":
    atualizar()
