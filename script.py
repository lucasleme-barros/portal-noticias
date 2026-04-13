import os
from google import genai
import feedparser
import time

# ==========================================
# 1. CONFIGURAÇÕES E CHAVE
# ==========================================
# Puxa a chave do cofre (Secrets) do GitHub
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)
RSS_FEED_URL = "http://feeds.bbci.co.uk/portuguese/rss.xml" 

# Template HTML (A "carroceria" do site)
HTML_TEMPLATE_INICIO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA News Portal</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #0f111a; color: #e0e0e0; margin: 0; padding: 0; }
        header { background: linear-gradient(90deg, #1a1c2c, #4a192c); padding: 40px 20px; text-align: center; border-bottom: 3px solid #ff4b2b; }
        header h1 { margin: 0; font-size: 2.5em; letter-spacing: 2px; }
        .container { max-width: 900px; margin: 30px auto; padding: 0 20px; }
        .noticia-card { background: #1e2030; padding: 30px; border-radius: 12px; margin-bottom: 25px; border-left: 5px solid #ff4b2b; box-shadow: 0 10px 20px rgba(0,0,0,0.5); }
        .noticia-card h2 { margin-top: 0; color: #fff; line-height: 1.3; }
        .noticia-card p { line-height: 1.8; color: #b0b3b8; font-size: 1.1em; }
        .tags { display: flex; gap: 10px; margin-top: 20px; }
        .tag { background: #30334a; padding: 5px 12px; border-radius: 20px; font-size: 0.8em; color: #ff4b2b; font-weight: bold; }
        footer { text-align: center; padding: 20px; font-size: 0.9em; color: #666; }
    </style>
</head>
<body>
    <header>
        <h1>PORTAL IA NEWS</h1>
        <p>Automação em tempo real com Gemini</p>
    </header>
    <div class="container">
"""

HTML_TEMPLATE_FIM = """
    </div>
    <footer>Gerado automaticamente via GitHub Actions e Gemini</footer>
</body>
</html>
"""

def processar_noticia(titulo, resumo):
    prompt = f"Reescreva esta notícia para um site moderno. Título original: {titulo}. Resumo: {resumo}. Retorne no formato: TITULO: [titulo] CORPO: [parágrafo] TAGS: [tag1, tag2]"
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        print(f"Erro na IA: {e}")
        return None

def formatar_para_html(conteudo_ia):
    try:
        linhas = conteudo_ia.split('\n')
        titulo = [l for l in linhas if "TITULO:" in l][0].replace("TITULO:", "").strip()
        corpo = [l for l in linhas if "CORPO:" in l][0].replace("CORPO:", "").strip()
        tags_raw = [l for l in linhas if "TAGS:" in l][0].replace("TAGS:", "").strip().split(',')
        
        tags_html = "".join([f'<span class="tag">{t.strip()}</span>' for t in tags_raw])
        
        return f"""
        <div class="noticia-card">
            <h2>{titulo}</h2>
            <p>{corpo}</p>
            <div class="tags">{tags_html}</div>
        </div>
        """
    except Exception as e:
        print(f"Erro na formatação: {e}")
        return ""

def gerar_site():
    print("Iniciando geração do site...")
    feed = feedparser.parse(RSS_FEED_URL)
    noticias_html = ""
    
    for entry in feed.entries[:5]:
        print(f"Processando: {entry.title[:50]}...")
        texto_ia = processar_noticia(entry.title, entry.summary)
        if texto_ia:
            noticias_html += formatar_para_html(texto_ia)
        time.sleep(2)

    conteudo_completo = HTML_TEMPLATE_INICIO + noticias_html + HTML_TEMPLATE_FIM
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(conteudo_completo)
    
    print("\n✅ SUCESSO! O arquivo 'index.html' foi criado.")

if __name__ == "__main__":
    gerar_site()
