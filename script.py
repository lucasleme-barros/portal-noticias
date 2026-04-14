import os
import google.generativeai as genai
import feedparser
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAÇÃO ---
CHAVE_GITHUB = os.environ.get("GEMINI_API_KEY")
if CHAVE_GITHUB:
    genai.configure(api_key=CHAVE_GITHUB)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

fuso = pytz.timezone('America/Sao_Paulo')
agora_str = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

# --- DICIONÁRIO DE FONTES (FEEDS) ---
FEEDS = {
    "Mundo_BBC": "https://feeds.bbci.co.uk/portuguese/rss.xml",
    "Mundo_Reuters": "https://www.reutersagency.com/feed/",
    "Esportes_GE": "https://ge.globo.com/rss/ge/",
    "Games_IGN": "https://br.ign.com/feed.xml",
    "Hardware_Adrenaline": "https://www.adrenaline.com.br/feed/",
    "Hardware_TechPowerUp": "https://www.techpowerup.com/rss/news",
    "C#_MS_Blog": "https://devblogs.microsoft.com/dotnet/feed/",
    "Cyber_CISO": "https://www.cisoadvisor.com.br/rss-feed/",
    "Tech_G1": "https://g1.globo.com/rss/g1/tecnologia/",
    "Esquerda_247": "https://www.brasil247.com/feed",
    "Centro_CNN": "https://www.cnnbrasil.com.br/politica/feed/",
    "Direita_Oeste": "https://revistaoeste.com/feed/"
}

CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 20px; text-align: center; border-bottom: 3px solid #d93025; }
    
    .search-container { padding: 10px; background: #fff; text-align: center; border-bottom: 1px solid #ddd; }
    #search-input { padding: 10px; width: 80%; max-width: 400px; border-radius: 20px; border: 1px solid #ccc; outline: none; }

    .filter-container { text-align: center; padding: 15px; position: sticky; top: 0; background: #f0f2f5; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; flex-direction: column; gap: 5px; }
    .filter-btn { background: #fff; border: 2px solid #ddd; padding: 6px 14px; margin: 2px; border-radius: 20px; cursor: pointer; font-weight: bold; font-size: 0.85em; }
    .filter-btn.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }

    .main-wrapper { display: flex; max-width: 1200px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1.2; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 180px; }
    
    .noticia-card { background: #fff; margin-bottom: 25px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; cursor: pointer; transition: 0.3s; position: relative; }
    .noticia-card:hover { transform: translateY(-3px); }
    
    .sentiment-tag { position: absolute; top: 10px; right: 10px; padding: 4px 8px; border-radius: 4px; font-size: 0.7em; font-weight: bold; color: #fff; z-index: 10; }
    .bg-positivo { background: #28a745; } .bg-negativo { background: #dc3545; } .bg-neutro { background: #6c757d; }

    .border-esquerda { border-left: 8px solid #d93025; } .border-direita { border-left: 8px solid #1a73e8; } .border-centro { border-left: 8px solid #6c757d; } .border-padrao { border-left: 8px solid #00c853; }

    .img-container { position: relative; width: 100%; padding-top: 56.25%; background: #eee; }
    .noticia-img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
    .noticia-body { padding: 15px; }
    .noticia-body h2 { margin: 5px 0; font-size: 1.2em; color: #1a73e8; }
    
    .modal { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); overflow-y: auto; }
    .modal-content { background: #fff; margin: 30px auto; padding: 30px; width: 90%; max-width: 700px; border-radius: 12px; position: relative; line-height: 1.7; }
    .fechar-modal { position: absolute; right: 20px; top: 10px; font-size: 30px; cursor: pointer; }
    
    @media (max-width: 800px) { .main-wrapper { flex-direction: column; } .sidebar { position: static; } }
</style>
"""

JS = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/lunr.js/2.3.9/lunr.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/timeago.js/2.0.2/timeago.min.js"></script>
<script>
    // Inicializar Tempo Relativo
    timeago().render(document.querySelectorAll('.timeago'), 'pt_BR');

    // Inicializar Motor de Busca
    let idx;
    function buildIndex() {
        const cards = document.querySelectorAll('.noticia-card');
        idx = lunr(function () {
            this.field('titulo');
            this.field('categoria');
            this.ref('id');
            cards.forEach(card => {
                this.add({
                    id: card.getAttribute('data-id'),
                    titulo: card.querySelector('h2').innerText,
                    categoria: card.getAttribute('data-categoria')
                });
            });
        });
    }

    function pesquisar() {
        const query = document.getElementById('search-input').value.toLowerCase();
        const cards = document.querySelectorAll('.noticia-card');
        if (!query) { cards.forEach(c => c.style.display = 'block'); return; }
        
        const results = idx.search(query).map(r => r.ref);
        cards.forEach(card => {
            const id = card.getAttribute('data-id');
            card.style.display = results.includes(id) ? 'block' : 'none';
        });
    }

    function filtrarNoticias(cat, btn) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cards = document.querySelectorAll('.noticia-card');
        cards.forEach(card => {
            const cardCat = card.getAttribute('data-categoria').toLowerCase();
            card.style.display = (cat === 'todas' || cardCat.includes(cat.toLowerCase())) ? 'block' : 'none';
        });
    }

    function abrirMateria(id) { document.getElementById('modal-' + id).style.display = 'block'; }
    function fecharMateria(id) { document.getElementById('modal-' + id).style.display = 'none'; }

    window.onload = buildIndex;
</script>
"""

def processar_noticia(titulo, resumo, categoria):
    if not model: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [SENTIMENTO] Neutro [FIM]"
    prompt = f"""Analista. Cat: {categoria}. Título: {titulo}. Resumo: {resumo}. 
    Gere: [MANCHETE] (Curta) [MATERIA] (3 parágrafos) [SENTIMENTO] (Positivo, Negativo ou Neutro) [FIM]"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [SENTIMENTO] Neutro [FIM]"

def gerar_pagina_individual(id_noticia, manchete, materia, img, cat, sentimento):
    if not os.path.exists("materia"): os.makedirs("materia")
    html = f"""<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>{manchete}</title>{CSS}</head>
    <body style='background:#fff;'><header><h1>Portal IA News</h1><a href='../index.html'>← Voltar</a></header>
    <div class='modal-content' style='margin-top:20px; box-shadow:none;'>
    <img src='{img}' style='width:100%; border-radius:8px;'><br><small>{cat} | Sentimento: {sentimento}</small>
    <h1>{manchete}</h1><div style='font-size:1.2em;'>{materia.replace(chr(10), '<br><br>')}</div>
    </div></body></html>"""
    with open(f"materia/{id_noticia}.html", "w", encoding="utf-8") as f: f.write(html)

def extrair_noticias_da_fonte(item):
    cat, url = item
    feed = feedparser.parse(url)
    cards_html, hist_html = "", ""
    adicionadas = 0
    for entry in feed.entries[:5]:
        texto_ia = processar_noticia(entry.title, entry.get('summary', ''), cat)
        try:
            manchete = texto_ia.split("[MANCHETE]")[1].split("[MATERIA]")[0].strip()
            materia = texto_ia.split("[MATERIA]")[1].split("[SENTIMENTO]")[0].strip()
            sentimento = texto_ia.split("[SENTIMENTO]")[1].split("[FIM]")[0].strip()
        except: manchete, materia, sentimento = entry.title, entry.get('summary', ''), "Neutro"

        id_noticia = str(int(time.time() * 1000) + hash(cat + entry.title))
        img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
        if 'media_content' in entry: img = entry.media_content[0].get('url', img)
        
        gerar_pagina_individual(id_noticia, manchete, materia, img, cat, sentimento)
        
        classe_sent = f"bg-{sentimento.lower()}"
        classe_cor = "border-esquerda" if "Esquerda" in cat else "border-direita" if "Direita" in cat else "border-centro" if "Centro" in cat else "border-padrao"
        data_iso = datetime.now(fuso).isoformat()

        cards_html += f'''
        <div class="noticia-card {classe_cor}" data-id="{id_noticia}" data-categoria="{cat}" onclick="abrirMateria('{id_noticia}')">
            <div class="sentiment-tag {classe_sent}">{sentimento}</div>
            <div class="img-container"><img src="{img}" class="noticia-img"></div>
            <div class="noticia-body">
                <small class="timeago" datetime="{data_iso}"></small> • <small><b>{cat.upper()}</b></small>
                <h2>{manchete}</h2>
                <a href="materia/{id_noticia}.html" style="font-size:0.8em; color:#1a73e8;" onclick="event.stopPropagation();">Link Direto</a>
            </div>
        </div>
        <div id="modal-{id_noticia}" class="modal">
            <div class="modal-content"><span class="fechar-modal" onclick="fecharMateria('{id_noticia}')">&times;</span>
            <img src="{img}" style="width:100%; border-radius:8px;"><h1>{manchete}</h1>
            <p>{materia.replace(chr(10), '<br><br>')}</p></div>
        </div>'''
        hist_html += f'<div class="historico-item"><b>{cat}</b>: {manchete}</div>'
        adicionadas += 1
    return cards_html, hist_html

def atualizar_portal():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            antigas = "".join([str(c) for c in soup.find_all(class_='noticia-card')[:40]])
            hist_antigo = "".join([str(i) for i in soup.find_all(class_='historico-item')[:50]])
    else: antigas, hist_antigo = "", ""

    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(extrair_noticias_da_fonte, FEEDS.items()))

    novas = "".join([r[0] for r in res]); novos_h = "".join([r[1] for r in res])
    
    filtros = """<div class="search-container"><input type="text" id="search-input" placeholder="Pesquisar notícias..." onkeyup="pesquisar()"></div>
    <div class="filter-container"><div><button class="filter-btn active" onclick="filtrarNoticias('todas', this)">🏠 Todas</button>
    <button class="filter-btn" onclick="filtrarNoticias('Esquerda', this)">🔴 Esquerda</button>
    <button class="filter-btn" onclick="filtrarNoticias('Direita', this)">🔵 Direita</button>
    <button class="filter-btn" onclick="filtrarNoticias('Hardware', this)">💻 Hardware</button>
    <button class="filter-btn" onclick="filtrarNoticias('C#', this)">🎯 C#</button></div></div>"""

    final = f"<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'>{CSS}</head><body><header><h1>Portal IA News</h1></header>{filtros}<div class='main-wrapper'><div class='content-area'>{novas}{antigas}</div><div class='sidebar'><h3>Histórico</h3><div class='sidebar-list'>{novos_h}{hist_antigo}</div></div></div>{JS}</body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(final)

if __name__ == "__main__": atualizar_portal()
