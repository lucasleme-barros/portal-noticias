import os
from google import genai
import feedparser
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# --- CONFIG ---
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)
fuso = pytz.timezone('America/Sao_Paulo')
agora_str = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

FEEDS = {
    "Mundo": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Tecnologia": "https://br.ign.com/feed.xml"
}

CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; }
    header { background: #fff; padding: 20px; text-align: center; border-bottom: 3px solid #d93025; }
    .main-wrapper { display: flex; max-width: 1200px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 8px; height: fit-content; border: 1px solid #ddd; }
    .noticia-card { background: #fff; margin-bottom: 25px; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; }
    .noticia-img { width: 100%; height: 280px; object-fit: cover; }
    .noticia-body { padding: 20px; }
    .historico-item { font-size: 0.85em; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px; }
    @media (max-width: 800px) { .main-wrapper { flex-direction: column; } }
</style>
"""

def processar_noticia(titulo, resumo):
    prompt = f"Aja como jornalista. Título: {titulo}. Resumo: {resumo}. Formato: [RESUMO] (Manchete) [MATERIA] (2 parágrafos) [FIM]"
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return response.text
    except: return None

def atualizar_portal():
    antigas_noticias = ""
    antigo_historico = ""
    
    # Tenta ler o que já existe
    if os.path.exists("index.html"):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                # Busca as áreas específicas ou pega o que der
                news_div = soup.find(class_='content-area')
                hist_div = soup.find(class_='sidebar-list')
                if news_div: antigas_noticias = "".join([str(c) for c in news_div.contents])
                if hist_div: antigo_historico = "".join([str(c) for c in hist_div.contents])
        except: pass

    novas_noticias = ""
    novos_historicos = ""
    
    for cat, url in FEEDS.items():
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            texto = processar_noticia(entry.title, entry.summary)
            if texto and "[RESUMO]" in texto:
                try:
                    resumo = texto.split("[RESUMO]")[1].split("[MATERIA]")[0].strip()
                    materia = texto.split("[MATERIA]")[1].split("[FIM]")[0].strip()
                    img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
                    
                    novas_noticias += f'<div class="noticia-card"><img src="{img}" class="noticia-img"><div class="noticia-body"><small>{agora_str}</small><h2>{resumo}</h2><p>{materia}</p></div></div>'
                    novos_historicos += f'<div class="historico-item"><b>{agora_str}</b>: {resumo}</div>'
                except: continue
            time.sleep(2)

    # Monta o HTML do Zero para garantir que não quebre
    final_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>IA News</title>{CSS}</head>
<body>
    <header><h1>IA News - Fluxo Contínuo</h1><p>Atualizado: {agora_str}</p></header>
    <div class="main-wrapper">
        <div class="content-area">{novas_noticias}{antigas_noticias}</div>
        <div class="sidebar"><h3>Histórico do Dia</h3><div class="sidebar-list">{novos_historicos}{antigo_historico}</div></div>
    </div>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    atualizar_portal()
