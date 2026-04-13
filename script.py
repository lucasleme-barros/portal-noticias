import os
import google.generativeai as genai
import feedparser
import time
from datetime import datetime
import pytz

# --- CONFIGURAÇÃO ---
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

fuso = pytz.timezone('America/Sao_Paulo')
agora_str = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

FEEDS = {
    "Mundo": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Tecnologia": "https://br.ign.com/feed.xml"
}

CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 3px solid #d93025; }
    .main-wrapper { display: flex; max-width: 1200px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 10px; }
    .noticia-card { background: #fff; margin-bottom: 25px; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; }
    .noticia-img { width: 100%; height: 280px; object-fit: cover; background: #eee; }
    .noticia-body { padding: 20px; }
    .historico-item { font-size: 0.85em; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px; }
    @media (max-width: 800px) { .main-wrapper { flex-direction: column; } .sidebar { position: static; } }
</style>
"""

def processar_noticia(titulo, resumo):
    prompt = f"Aja como um jornalista profissional. Reescreva de forma envolvente em dois parágrafos: Título: {titulo}. Resumo original: {resumo}."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Falha na IA: {e}")
        return resumo # Se a IA falhar, usamos o resumo original para o site não ficar vazio

def atualizar_portal():
    novas_noticias = ""
    novos_historicos = ""
    
    print("Iniciando coleta...")
    for cat, url in FEEDS.items():
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            texto_ia = processar_noticia(entry.title, entry.summary)
            img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
            
            # Monta Card
            novas_noticias += f'''
            <div class="noticia-card">
                <img src="{img}" class="noticia-img">
                <div class="noticia-body">
                    <small style="color:#d93025; font-weight:bold;">{cat} • {agora_str}</small>
                    <h2 style="margin-top:10px;">{entry.title}</h2>
                    <p>{texto_ia}</p>
                </div>
            </div>
            '''
            # Monta Sidebar
            novos_historicos += f'<div class="historico-item"><b>{agora_str}</b>: {entry.title}</div>'
            time.sleep(1)

    # MONTAGEM FINAL
    final_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>IA News Portal</title>{CSS}</head>
<body>
    <header><h1>Portal IA News - Fluxo Contínuo</h1><p>Última atualização: {agora_str}</p></header>
    <div class="main-wrapper">
        <div class="content-area">{novas_noticias}</div>
        <div class="sidebar"><h3>Histórico do Dia</h3><div class="sidebar-list">{novos_historicos}</div></div>
    </div>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    print("✅ Site atualizado com sucesso!")

if __name__ == "__main__":
    atualizar_portal()
