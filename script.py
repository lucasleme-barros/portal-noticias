import os
import google.generativeai as genai
import feedparser
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# --- CONFIG ---
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
    "Games": "https://br.ign.com/feed.xml",
    "Hardware": "https://www.adrenaline.com.br/feed/",
    "Tecnologia": "https://g1.globo.com/rss/g1/tecnologia/",
    "DotNet_CS": "https://devblogs.microsoft.com/dotnet/feed/",
    "Dev_Brasil": "https://www.infoq.com/br/feed/",
    "Cybersecurity": "https://www.cisoadvisor.com.br/rss-feed/",
    "Geral": "https://www.cnnbrasil.com.br/feed/",
    
    # --- POLÍTICA ORGANIZADA ---
    "Esquerda": "https://www.brasil247.com/feed",
    "Esquerda ": "https://www.diariodocentrodomundo.com.br/feed/",
    "Centro": "https://www.cnnbrasil.com.br/politica/feed/",
    "Centro ": "https://g1.globo.com/rss/g1/politica/",
    "Direita": "https://www.gazetadopovo.com.br/feed/rss/rodrigo-constantino.xml",
    "Direita ": "https://revistaoeste.com/feed/"
}

CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 3px solid #d93025; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    
    .filter-container { 
        text-align: center; 
        margin: 0; 
        padding: 15px;
        position: sticky;
        top: 0;
        background: #f0f2f5;
        z-index: 100;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .filter-btn {
        background: #fff;
        border: 2px solid #ddd;
        padding: 8px 18px;
        margin: 5px;
        border-radius: 20px;
        cursor: pointer;
        font-weight: bold;
        transition: 0.3s;
    }
    .filter-btn:hover { background: #e8f0fe; border-color: #1a73e8; }
    .filter-btn.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }

    .main-wrapper { display: flex; max-width: 1000px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 80px; }
    
    .noticia-card { background: #fff; margin-bottom: 30px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; cursor: pointer; transition: 0.3s; }
    .noticia-card:hover { transform: translateY(-5px); }
    
    .border-esquerda { border-left: 8px solid #d93025 !important; }
    .border-direita { border-left: 8px solid #1a73e8 !important; }
    .border-centro { border-left: 8px solid #6c757d !important; }
    .border-padrao { border-left: 8px solid #eee; }

    .img-container { position: relative; width: 100%; padding-top: 56.25%; background: #eee; }
    .noticia-img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
    .noticia-body { padding: 20px; }
    .noticia-body h2 { margin: 10px 0; font-size: 1.4em; color: #1a73e8; line-height: 1.2; }
    
    .modal { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); overflow-y: auto; }
    .modal-content { background: #fff; margin: 30px auto; padding: 30px; width: 90%; max-width: 750px; border-radius: 12px; position: relative; line-height: 1.6; }
    .fechar-modal { position: absolute; right: 20px; top: 10px; font-size: 35px; cursor: pointer; color: #aaa; }
    
    .historico-item { font-size: 0.85em; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    @media (max-width: 800px) { .main-wrapper { flex-direction: column; } }
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

function filtrarNoticias(categoria, btn) {
    const cards = document.querySelectorAll('.noticia-card');
    const botoes = document.querySelectorAll('.filter-btn');
    
    botoes.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    cards.forEach(card => {
        const cardCat = card.getAttribute('data-categoria');
        if (categoria === 'todas' || cardCat.includes(categoria)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}
</script>
"""

def processar_noticia(titulo, resumo, categoria):
    if model:
        prompt = f"Aja como um analista de notícias. Categoria: {categoria}. Título: {titulo}. Resumo: {resumo}. Gere: [MANCHETE] (Curta) [MATERIA] (3 parágrafos focados no contexto da categoria) [FIM]"
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
                    cards = area_news.find_all(class_='noticia-card')[:20]
                    modais = area_news.find_all(class_='modal')[:20]
                    antigas_noticias = "".join([str(c) for c in cards]) + "".join([str(m) for m in modais])
                if area_hist:
                    itens = area_hist.find_all(class_='historico-item')[:25]
                    antigo_historico = "".join([str(i) for i in itens])
        except: pass

    novas_noticias = ""
    novos_historicos = ""
    
    for cat, url in FEEDS.items():
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            texto_ia = processar_noticia(entry.title, entry.summary, cat)
            
            classe_cor = "border-padrao"
            if "Esquerda" in cat: classe_cor = "border-esquerda"
            elif "Direita" in cat: classe_cor = "border-direita"
            elif "Centro" in cat: classe_cor = "border-centro"

            try:
                manchete = texto_ia.split("[MANCHETE]")[1].split("[MATERIA]")[0].strip()
                materia = texto_ia.split("[MATERIA]")[1].split("[FIM]")[0].strip()
            except:
                manchete, materia = entry.title, entry.summary

            id_noticia = int(time.time() * 1000) + hash(cat)
            img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
            if 'media_content' in entry: img = entry.media_content[0]['url']
            elif 'links' in entry:
                for link in entry.links:
                    if 'image' in link.get('type', ''): img = link.get('href')

            novas_noticias += f'''
            <div class="noticia-card {classe_cor}" data-categoria="{cat}" onclick="abrirMateria('{id_noticia}')">
                <div class="img-container">
                    <img src="{img}" class="noticia-img">
                </div>
                <div class="noticia-body">
                    <small style="color:#666; font-weight:bold;">{cat.upper()} • {agora_str}</small>
                    <h2>{manchete}</h2>
                </div>
            </div>
            
            <div id="modal-{id_noticia}" class="modal">
                <div class="modal-content">
                    <span class="fechar-modal" onclick="fecharMateria('{id_noticia}')">&times;</span>
                    <div class="img-container" style="margin-bottom:20px;">
                        <img src="{img}" class="noticia-img">
                    </div>
                    <small>{cat.upper()}</small>
                    <h1>{manchete}</h1>
                    <div style="font-size:1.1em; color:#333;">{materia.replace(chr(10), '<br><br>')}</div>
                </div>
            </div>
            '''
            novos_historicos += f'<div class="historico-item"><b>{cat}</b>: {manchete}</div>'
            time.sleep(1)

    botoes_filtro = """
    <div class="filter-container">
        <button class="filter-btn active" onclick="filtrarNoticias('todas', this)">Todas</button>
        <button class="filter-btn" onclick="filtrarNoticias('Esquerda', this)">Esquerda</button>
        <button class="filter-btn" onclick="filtrarNoticias('Centro', this)">Centro</button>
        <button class="filter-btn" onclick="filtrarNoticias('Direita', this)">Direita</button>
    </div>
    """

    final_html = f"""
    <!DOCTYPE html>
    <html lang='pt-BR'>
    <head><meta charset='UTF-8'>{CSS}</head>
    <body>
        <header><h1>Portal IA News</h1></header>
        {botoes_filtro}
        <div class='main-wrapper'>
            <div class='content-area'>{novas_noticias}{antigas_noticias}</div>
            <div class='sidebar'>
                <h3>Histórico</h3>
                <div class='sidebar-list'>{novos_historicos}{antigo_historico}</div>
            </div>
        </div>
        {JS}
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    atualizar_portal()
