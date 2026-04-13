import os
from google import genai
import feedparser
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup # Necessário adicionar 'beautifulsoup4' no requirements.txt

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)
fuso = pytz.timezone('America/Sao_Paulo')
agora_str = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

FEEDS = {
    "Mundo": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Tecnologia": "https://br.ign.com/feed.xml"
}

# ==========================================
# 2. ESTILO CSS (Com Barra Lateral)
# ==========================================
CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; }
    header { background: #fff; padding: 20px; text-align: center; border-bottom: 2px solid #d93025; }
    .main-wrapper { display: flex; max-width: 1200px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    
    /* Coluna Principal */
    .content-area { flex: 3; }
    .noticia-card { background: #fff; margin-bottom: 20px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .noticia-img { width: 100%; height: 250px; object-fit: cover; }
    .noticia-body { padding: 20px; }
    
    /* Barra Lateral */
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 8px; height: fit-content; position: sticky; top: 20px; }
    .sidebar h3 { border-bottom: 2px solid #1a73e8; padding-bottom: 10px; font-size: 1em; }
    .historico-item { font-size: 0.85em; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; color: #555; }
    
    @media (max-width: 768px) { .main-wrapper { flex-direction: column; } .sidebar { position: static; } }
</style>
"""

# ==========================================
# 3. LÓGICA DE PROCESSAMENTO
# ==========================================

def processar_noticia(titulo, resumo):
    prompt = f"Crie uma notícia curta. Título: {titulo}. Resumo: {resumo}. Formato: [RESUMO] (Manchete) [MATERIA] (Texto) [FIM]"
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return response.text
    except: return None

def gerar_html_noticia(texto_ia, img_url, id_noticia):
    try:
        resumo = texto_ia.split("[RESUMO]")[1].split("[MATERIA]")[0].strip()
        materia = texto_ia.split("[MATERIA]")[1].split("[FIM]")[0].strip()
        return f"""
        <div class="noticia-card" id="news-{id_noticia}">
            <img src="{img_url}" class="noticia-img">
            <div class="noticia-body">
                <small style="color:red">{agora_str}</small>
                <h2>{resumo}</h2>
                <p>{materia}</p>
            </div>
        </div>
        """, resumo
    except: return "", ""

def atualizar_portal():
    # 1. Tenta ler o arquivo atual para manter o histórico
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            antigas_noticias = str(soup.find(class_='content-area'))
            antigo_historico = str(soup.find(class_='sidebar-list'))
    else:
        antigas_noticias = '<div class="content-area"></div>'
        antigo_historico = '<div class="sidebar-list"></div>'

    nova_noticia_html = ""
    novo_item_sidebar = ""
    
    # 2. Coleta uma notícia fresca de cada feed
    for cat, url in FEEDS.items():
        feed = feedparser.parse(url)
        entry = feed.entries[0]
        img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=500"
        
        texto = processar_noticia(entry.title, entry.summary)
        if texto:
            card, titulo = gerar_html_noticia(texto, img, time.time())
            nova_noticia_html += card
            novo_item_sidebar += f'<div class="historico-item"><b>{agora_str}</b>: {titulo}</div>'

    # 3. Monta o arquivo final (Novas notícias entram ANTES das antigas)
    final_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8">{CSS}</head>
    <body>
        <header><h1>IA News - Fluxo Contínuo</h1></header>
        <div class="main-wrapper">
            <div class="content-area">
                {nova_noticia_html}
                {antigas_noticias.replace('<div class="content-area">', '').replace('</div>', '')}
            </div>
            <div class="sidebar">
                <h3>Histórico do Dia</h3>
                <div class="sidebar-list">
                    {novo_item_sidebar}
                    {antigo_historico.replace('<div class="sidebar-list">', '').replace('</div>', '')}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    atualizar_portal()
