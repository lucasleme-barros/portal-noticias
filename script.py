import os
import google.generativeai as genai
import feedparser
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# --- CONFIGURAÇÃO ---
CHAVE_GITHUB = os.environ.get("GEMINI_API_KEY")
if CHAVE_GITHUB:
    genai.configure(api_key=CHAVE_GITHUB)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

fuso = pytz.timezone('America/Sao_Paulo')
agora_str = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

FEEDS = {
    "Mundo": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Tecnologia": "https://br.ign.com/feed.xml"
}

# CSS com imagens mais baixas (200px) e design limpo
CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 3px solid #d93025; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .main-wrapper { display: flex; max-width: 1200px; margin: 25px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 10px; }
    .noticia-card { background: #fff; margin-bottom: 25px; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #eee; }
    .noticia-img { width: 100%; height: 200px; object-fit: cover; background: #eee; }
    .noticia-body { padding: 20px; }
    .historico-item { font-size: 0.85em; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    @media (max-width: 850px) { .main-wrapper { flex-direction: column; } .sidebar { position: static; } }
</style>
"""

def processar_noticia(titulo, resumo):
    if model:
        prompt = f"Aja como jornalista. Reescreva em dois parágrafos de forma envolvente: Título: {titulo}. Resumo: {resumo}."
        try:
            response = model.generate_content(prompt)
            return response.text
        except: return resumo
    return resumo

def atualizar_portal():
    antigas_noticias = ""
    antigo_historico = ""
    
    # Lógica para ler o conteúdo atual e permitir o acúmulo (Volume)
    if os.path.exists("index.html"):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                area_news = soup.find(class_='content-area')
                area_hist = soup.find(class_='sidebar-list')
                if area_news:
                    # Mantém apenas as últimas 15 notícias para não pesar o arquivo
                    noticias_atuais = area_news.find_all(class_='noticia-card')[:15]
                    antigas_noticias = "".join([str(n) for n in noticias_atuais])
                if area_hist:
                    itens_hist = area_hist.find_all(class_='historico-item')[:20]
                    antigo_historico = "".join([str(i) for i in itens_hist])
        except: pass

    novas_noticias = ""
    novos_historicos = ""
    
    for cat, url in FEEDS.items():
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            texto = processar_noticia(entry.title, entry.summary)
            img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
            if 'media_content' in entry: img = entry.media_content[0]['url']
            
            novas_noticias += f'''
            <div class="noticia-card">
                <img src="{img}" class="noticia-img">
                <div class="noticia-body">
                    <small style="color:#d93025; font-weight:bold;">{cat.upper()} • {agora_str}</small>
                    <h2 style="margin: 10px 0;">{entry.title}</h2>
                    <p>{texto}</p>
                </div>
            </div>'''
            novos_historicos += f'<div class="historico-item"><b>{agora_str}</b><br>{entry.title}</div>'
            time.sleep(1)

    final_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Portal IA News</title>{CSS}</head>
<body>
    <header><h1>Portal IA News</h1><p>Atualizado em {agora_str}</p></header>
    <div class="main-wrapper">
        <div class="content-area">{novas_noticias}{antigas_noticias}</div>
        <div class="sidebar"><h3>Histórico</h3><div class="sidebar-list">{novos_historicos}{antigo_historico}</div></div>
    </div>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    atualizar_portal()
