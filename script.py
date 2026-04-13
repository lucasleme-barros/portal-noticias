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

# CSS COM MODAL E IMAGENS AJUSTADAS
CSS = """
<style>
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 20px; text-align: center; border-bottom: 3px solid #d93025; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    
    .main-wrapper { display: flex; max-width: 1100px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 10px; }
    
    .noticia-card { background: #fff; margin-bottom: 20px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; cursor: pointer; transition: 0.3s; }
    .noticia-card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.15); }
    
    .noticia-img { width: 100%; height: 200px; object-fit: cover; background: #eee; border-bottom: 1px solid #eee; }
    .noticia-body { padding: 15px; }
    .noticia-body h2 { margin: 10px 0; font-size: 1.3em; line-height: 1.2; color: #1a73e8; }
    
    /* MODAL (JANELA DA NOTÍCIA COMPLETA) */
    .modal { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); overflow-y: auto; }
    .modal-content { background: #fff; margin: 5% auto; padding: 30px; width: 90%; max-width: 700px; border-radius: 12px; position: relative; line-height: 1.8; }
    .fechar-modal { position: absolute; right: 20px; top: 10px; font-size: 30px; cursor: pointer; color: #aaa; }
    .modal-img { width: 100%; height: 300px; object-fit: cover; border-radius: 8px; margin-bottom: 20px; }
    
    .historico-item { font-size: 0.8em; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px; }
    @media (max-width: 800px) { .main-wrapper { flex-direction: column; } .sidebar { position: static; } }
</style>
"""

JS = """
<script>
function abrirMateria(id) {
    document.getElementById('modal-' + id).style.display = 'block';
    document.body.style.overflow = 'hidden';
}
function fecharMateria(id) {
    document.getElementById('modal-' + id).style.display = 'none';
    document.body.style.overflow = 'auto';
}
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}
</script>
"""

def processar_noticia(titulo, resumo):
    if model:
        # Pedimos agora uma manchete curta e uma matéria completa em 3 parágrafos
        prompt = f"Aja como jornalista. Título: {titulo}. Resumo: {resumo}. Gere: [MANCHETE] (Curta) [MATERIA] (3 parágrafos detalhados) [FIM]"
        try:
            response = model.generate_content(prompt)
            return response.text
        except: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [FIM]"
    return f"[MANCHETE] {titulo} [MATERIA] {resumo} [FIM]"

def atualizar_portal():
    antigas_noticias = ""
    antigo_historico = ""
    
    if os.path.exists("index.html"):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                area_news = soup.find(class_='content-area')
                area_hist = soup.find(class_='sidebar-list')
                if area_news:
                    # Mantém os últimos 10 cards no histórico visual
                    cards = area_news.find_all(lambda tag: tag.name == 'div' and 'noticia-card' in tag.get('class', []))[:10]
                    modais = area_news.find_all(class_='modal')[:10]
                    antigas_noticias = "".join([str(c) for c in cards]) + "".join([str(m) for m in modais])
                if area_hist:
                    itens = area_hist.find_all(class_='historico-item')[:15]
                    antigo_historico = "".join([str(i) for i in itens])
        except: pass

    novas_noticias = ""
    novos_historicos = ""
    
    for cat, url in FEEDS.items():
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            texto_ia = processar_noticia(entry.title, entry.summary)
            
            try:
                manchete = texto_ia.split("[MANCHETE]")[1].split("[MATERIA]")[0].strip()
                materia = texto_ia.split("[MATERIA]")[1].split("[FIM]")[0].strip()
            except:
                manchete = entry.title
                materia = entry.summary

            id_noticia = int(time.time() * 1000)
            img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
            if 'media_content' in entry: img = entry.media_content[0]['url']

            # CARD (O QUE APARECE NA HOME)
            novas_noticias += f'''
            <div class="noticia-card" onclick="abrirMateria('{id_noticia}')">
                <img src="{img}" class="noticia-img">
                <div class="noticia-body">
                    <small style="color:#d93025; font-weight:bold;">{cat.upper()} • {agora_str}</small>
                    <h2>{manchete}</h2>
                    <p style="color:#666; font-size:0.9em;">Clique para ler a matéria completa...</p>
                </div>
            </div>
            
            <div id="modal-{id_noticia}" class="modal">
                <div class="modal-content">
                    <span class="fechar-modal" onclick="fecharMateria('{id_noticia}')">&times;</span>
                    <img src="{img}" class="modal-img">
                    <small style="color:#d93025;">{cat.upper()} • {agora_str}</small>
                    <h1 style="margin-top:10px; line-height:1.2;">{manchete}</h1>
                    <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                    <div style="font-size:1.1em; color:#333;">{materia.replace(chr(10), '<br><br>')}</div>
                </div>
            </div>
            '''
            novos_historicos += f'<div class="historico-item"><b>{agora_str}</b><br>{manchete}</div>'
            time.sleep(1)

    final_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Portal IA News</title>{CSS}</head>
<body>
    <header><h1>Portal IA News</h1><p>Clique nas notícias para ler a matéria completa</p></header>
    <div class="main-wrapper">
        <div class="content-area">{novas_noticias}{antigas_noticias}</div>
        <div class="sidebar"><h3>Histórico</h3><div class="sidebar-list">{novos_historicos}{antigo_historico}</div></div>
    </div>
    {JS}
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    atualizar_portal()
