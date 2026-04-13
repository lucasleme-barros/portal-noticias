import os
from google import genai
import feedparser
import time
from datetime import datetime
import pytz

# ==========================================
# 1. CONFIGURAÇÕES, CHAVE E DATAS
# ==========================================
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)

fuso = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso).strftime('%d/%m/%Y %H:%M:%S')

FEEDS = {
    "Mundo & Atualidades": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Games & Tecnologia": "https://br.ign.com/feed.xml"
}

# ==========================================
# 2. TEMPLATES HTML (Com suporte a Imagem)
# ==========================================
HTML_TEMPLATE_INICIO = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA News Portal</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #0f111a; color: #e0e0e0; margin: 0; padding: 0; }}
        header {{ background: linear-gradient(90deg, #1a1c2c, #4a192c); padding: 40px 20px; text-align: center; border-bottom: 3px solid #ff4b2b; }}
        header h1 {{ margin: 0; font-size: 2.5em; letter-spacing: 2px; text-transform: uppercase; }}
        header p {{ color: #b0b3b8; font-size: 0.9em; margin-top: 10px; }}
        
        .container {{ max-width: 1100px; margin: 30px auto; padding: 0 20px; }}
        .categoria-titulo {{ color: #ff4b2b; border-bottom: 2px solid #30334a; padding-bottom: 10px; margin-top: 40px; margin-bottom: 20px; font-size: 1.8em; text-transform: uppercase; }}
        
        .grid-noticias {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; }}
        
        .noticia-card {{ background: #1e2030; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 15px rgba(0,0,0,0.4); display: flex; flex-direction: column; transition: transform 0.3s; border-bottom: 4px solid #ff4b2b; }}
        .noticia-card:hover {{ transform: translateY(-5px); }}
        
        .noticia-img {{ width: 100%; height: 200px; object-fit: cover; background-color: #2a2d3e; }}
        
        .noticia-content {{ padding: 20px; flex-grow: 1; display: flex; flex-direction: column; }}
        .noticia-card h2 {{ margin-top: 0; color: #fff; font-size: 1.25em; line-height: 1.3; }}
        .noticia-card p {{ line-height: 1.5; color: #b0b3b8; font-size: 0.95em; flex-grow: 1; }}
        
        .tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 15px; }}
        .tag {{ background: #30334a; padding: 4px 10px; border-radius: 15px; font-size: 0.7em; color: #03dac6; font-weight: bold; }}
        
        footer {{ text-align: center; padding: 30px; font-size: 0.8em; color: #666; margin-top: 50px; background: #0a0b10; }}
    </style>
</head>
<body>
    <header>
        <h1>Portal IA News</h1>
        <p>Última atualização: {agora}</p>
    </header>
    <div class="container">
"""

HTML_TEMPLATE_FIM = """
    </div>
    <footer>
        <p>Sistema Autônomo de Notícias • Desenvolvido com Gemini</p>
    </footer>
</body>
</html>
"""

# ==========================================
# 3. FUNÇÕES DE APOIO
# ==========================================
def extrair_imagem(entry):
    # Tenta encontrar imagem no feed (tags comuns como media_content ou links no sumário)
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''):
                return link.get('href')
    # Imagem padrão se falhar
    return "https://images.unsplash.com/photo-1585829365234-781f75d931f4?q=80&w=500&auto=format&fit=crop"

def processar_noticia(titulo, resumo):
    prompt = f"Reescreva para um portal. Título: {titulo}. Resumo: {resumo}. Formato: TITULO: [t] CORPO: [p] TAGS: [t1, t2]"
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except: return None

def formatar_para_html(conteudo_ia, url_img):
    try:
        linhas = conteudo_ia.split('\n')
        titulo = [l for l in linhas if "TITULO:" in l][0].replace("TITULO:", "").strip()
        corpo = [l for l in linhas if "CORPO:" in l][0].replace("CORPO:", "").strip()
        tags_raw = [l for l in linhas if "TAGS:" in l][0].replace("TAGS:", "").strip().split(',')
        tags_html = "".join([f'<span class="tag">{t.strip()}</span>' for t in tags_raw])
        
        return f"""
        <div class="noticia-card">
            <img class="noticia-img" src="{url_img}" alt="Imagem da notícia">
            <div class="noticia-content">
                <h2>{titulo}</h2>
                <p>{corpo}</p>
                <div class="tags">{tags_html}</div>
            </div>
        </div>
        """
    except: return ""

def gerar_site():
    print(f"Atualizando portal com imagens...")
    conteudo_dinamico = ""
    for categoria, url in FEEDS.items():
        conteudo_dinamico += f"<h2 class='categoria-titulo'>{categoria}</h2>\n<div class='grid-noticias'>"
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            url_img = extrair_imagem(entry)
            texto_ia = processar_noticia(entry.title, entry.summary)
            if texto_ia:
                conteudo_dinamico += formatar_para_html(texto_ia, url_img)
            time.sleep(3)
        conteudo_dinamico += "</div>\n"

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE_INICIO + conteudo_dinamico + HTML_TEMPLATE_FIM)
    print("✅ Sucesso!")

if __name__ == "__main__":
    gerar_site()
