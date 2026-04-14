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

FEEDS = {
    "Mundo_BBC": "https://feeds.bbci.co.uk/portuguese/rss.xml",
    "Geral_G1": "https://g1.globo.com/rss/g1/",
    "Hardware_Adrenaline": "https://www.adrenaline.com.br/feed/",
    "C#_MS_Blog": "https://devblogs.microsoft.com/dotnet/feed/",
    "Cyber_CISO": "https://www.cisoadvisor.com.br/rss-feed/",
    "Games_IGN": "https://br.ign.com/feed.xml",
    "Esquerda_247": "https://www.brasil247.com/feed",
    "Centro_CNN_Pol": "https://www.cnnbrasil.com.br/politica/feed/",
    "Direita_Oeste": "https://revistaoeste.com/feed/",
    "Tech_Gizmodo": "https://gizmodo.uol.com.br/feed/"
}

CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #fff; margin: 0; color: #333; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 1px solid #eee; position: relative; }
    
    .weather-widget { position: absolute; top: 10px; right: 20px; font-size: 0.85em; color: #555; background: #f9f9f9; padding: 5px 12px; border-radius: 15px; border: 1px solid #eee; display: flex; align-items: center; gap: 8px; cursor: pointer; }
    .weather-city { font-weight: bold; text-decoration: underline; }

    .search-container { padding: 15px; text-align: center; background: #f6f6f6; border-bottom: 1px solid #eee; }
    #search-input { padding: 10px 20px; width: 80%; max-width: 400px; border-radius: 25px; border: 1px solid #ddd; outline: none; }

    .filter-container { padding: 10px; background: #fff; border-bottom: 1px solid #eee; text-align: center; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .filter-group { margin-bottom: 5px; }
    .filter-btn { background: none; border: none; padding: 5px 12px; margin: 2px; cursor: pointer; font-weight: bold; font-size: 0.75em; color: #d93025; text-transform: uppercase; transition: 0.3s; }
    .filter-btn.active { background: #d93025; color: #fff; border-radius: 4px; }

    .main-wrapper { max-width: 1300px; margin: 20px auto; padding: 0 20px; display: flex; gap: 30px; }
    
    /* GRID ESTILO G1 */
    .content-area { 
        flex: 3;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 25px;
    }

    .noticia-card { background: #fff; padding-bottom: 20px; cursor: pointer; transition: 0.3s; position: relative; border-bottom: 1px solid #f0f0f0; }
    .noticia-card:hover { opacity: 0.8; }
    
    .sentiment-tag { font-size: 0.65em; font-weight: bold; text-transform: uppercase; padding: 2px 6px; border-radius: 3px; margin-bottom: 8px; display: inline-block; color: #fff; }
    .bg-positivo { background: #28a745; } .bg-negativo { background: #dc3545; } .bg-neutro { background: #6c757d; }

    .img-container { width: 100%; aspect-ratio: 16/9; background: #f8f8f8; border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
    .noticia-img { width: 100%; height: 100%; object-fit: cover; }
    
    .noticia-body h2 { margin: 0; font-size: 1.2em; line-height: 1.25; font-weight: 700; color: #111; }
    .noticia-body p { font-size: 0.9em; color: #555; margin: 10px 0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.4; }
    
    .tag-item { font-size: 0.7em; color: #d93025; font-weight: bold; margin-right: 8px; }

    .ad-slot { grid-column: 1 / -1; background: #fdfdfd; padding: 20px; border: 1px dashed #ccc; text-align: center; color: #999; font-size: 0.8em; border-radius: 8px; }

    .sidebar { flex: 1; border-left: 1px solid #eee; padding-left: 20px; max-width: 300px; }
    .sidebar h3 { font-size: 0.85em; text-transform: uppercase; color: #d93025; border-bottom: 2px solid #d93025; display: inline-block; margin-bottom: 15px; }
    .historico-item { font-size: 0.85em; margin-bottom: 15px; border-bottom: 1px solid #f6f6f6; padding-bottom: 10px; }
    .historico-item b { color: #d93025; font-size: 0.75em; text-transform: uppercase; }

    .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); overflow-y: auto; }
    .modal-content { background: #fff; margin: 2% auto; padding: 30px; width: 90%; max-width: 700px; border-radius: 12px; position: relative; }
    .fechar-modal { position: absolute; right: 20px; top: 10px; font-size: 30px; cursor: pointer; color: #aaa; }

    @media (max-width: 900px) { .main-wrapper { flex-direction: column; } .content-area { grid-template-columns: 1fr; } .sidebar { border-left: none; padding-left: 0; } .weather-widget { position: static; margin: 10px auto; width: fit-content; } }
</style>
"""

JS = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/lunr.js/2.3.9/lunr.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/timeago.js/2.0.2/timeago.min.js"></script>
<script>
    async function carregarClima(cidadeManual = null) {
        const display = document.getElementById('weather-display');
        let lat, lon, nomeCidade;
        const cidadeSalva = cidadeManual || localStorage.getItem('user_city');
        try {
            if (cidadeSalva) {
                const geo = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${cidadeSalva}&count=1&language=pt`).then(r => r.json());
                lat = geo.results[0].latitude; lon = geo.results[0].longitude; nomeCidade = geo.results[0].name;
                localStorage.setItem('user_city', nomeCidade);
            } else {
                const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej));
                lat = pos.coords.latitude; lon = pos.coords.longitude;
                const rev = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`).then(r => r.json());
                nomeCidade = rev.address.city || rev.address.town || "Sua Região";
            }
            const w = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`).then(r => r.json());
            display.innerHTML = `<span onclick="alterarCidade(event)" class="weather-city">📍 ${nomeCidade}</span>: <b>${Math.round(w.current_weather.temperature)}°C</b>`;
        } catch (e) { display.innerHTML = `<span onclick="alterarCidade(event)">📍 Definir Local</span>`; }
    }

    function alterarCidade(e) { e.stopPropagation(); const n = prompt("Cidade:"); if (n) carregarClima(n); }

    let idx;
    function buildIndex() {
        const cards = document.querySelectorAll('.noticia-card');
        idx = lunr(function () {
            this.field('titulo'); this.field('categoria'); this.ref('id');
            cards.forEach(c => this.add({ id: c.getAttribute('data-id'), titulo: c.querySelector('h2').innerText, categoria: c.getAttribute('data-categoria') }));
        });
    }

    function pesquisar() {
        const q = document.getElementById('search-input').value.toLowerCase();
        const cards = document.querySelectorAll('.noticia-card');
        if (!q) { cards.forEach(c => c.style.display = 'block'); return; }
        const res = idx.search(q).map(r => r.ref);
        cards.forEach(c => c.style.display = res.includes(c.getAttribute('data-id')) ? 'block' : 'none');
    }

    function filtrarNoticias(cat, btn) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.noticia-card').forEach(c => {
            const cardCat = c.getAttribute('data-categoria').toLowerCase();
            c.style.display = (cat === 'todas' || cardCat.includes(cat.toLowerCase())) ? 'block' : 'none';
        });
    }

    function abrirMateria(id) { document.getElementById('modal-' + id).style.display = 'block'; document.body.style.overflow = 'hidden'; }
    function fecharMateria(id) { document.getElementById('modal-' + id).style.display = 'none'; document.body.style.overflow = 'auto'; }
    window.onclick = (e) => { if (e.target.className === 'modal') { e.target.style.display = 'none'; document.body.style.overflow = 'auto'; } };

    window.onload = () => { buildIndex(); carregarClima(); timeago().render(document.querySelectorAll('.timeago'), 'pt_BR'); };
</script>
"""

def processar_noticia(titulo, resumo, categoria):
    if not model: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [SENTIMENTO] Neutro [TAGS] Notícia [FIM]"
    prompt = f"Analista G1. Cat: {categoria}. Título: {titulo}. Resumo: {resumo}. Gere: [MANCHETE] (Curta/Forte) [MATERIA] (3 parágrafos analíticos) [SENTIMENTO] (Positivo, Negativo ou Neutro) [TAGS] (3 tags separadas por vírgula) [FIM]"
    try: return model.generate_content(prompt).text
    except: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [SENTIMENTO] Neutro [TAGS] Geral [FIM]"

def gerar_pagina_individual(id_noticia, manchete, materia, img, cat, sentimento, tags):
    os.makedirs("materia", exist_ok=True)
    html = f"""<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><meta name="keywords" content="{tags}"><title>{manchete}</title>{CSS}</head>
    <body style='background:#fff;'><header><a href='../index.html' style='position:absolute; left:20px; top:25px; text-decoration:none; color:#d93025; font-weight:bold;'>← VOLTAR</a><h1>Portal IA News</h1></header>
    <article class='modal-content' style='box-shadow:none; border:1px solid #eee;'>
    <img src='{img}' style='width:100%; border-radius:12px;'>
    <div style='margin:20px 0;'><span class='sentiment-tag bg-{sentimento.lower()}'>{sentimento}</span> <small>| {cat}</small></div>
    <h1>{manchete}</h1><div style='font-size:1.2em; line-height:1.6;'>{materia.replace(chr(10), '<br><br>')}</div>
    <div style='margin-top:40px; padding-top:20px; border-top:1px solid #eee;'><small>Tags: {tags}</small></div></article></body></html>"""
    with open(f"materia/{id_noticia}.html", "w", encoding="utf-8") as f: f.write(html)

def extrair_noticias_da_fonte(item):
    cat, url = item
    feed = feedparser.parse(url)
    cards_html, hist_html = "", ""
    adicionadas = 0
    for entry in feed.entries[:6]:
        raw = processar_noticia(entry.title, entry.get('summary', ''), cat)
        try:
            manchete = raw.split("[MANCHETE]")[1].split("[MATERIA]")[0].strip()
            materia = raw.split("[MATERIA]")[1].split("[SENTIMENTO]")[0].strip()
            sentimento = raw.split("[SENTIMENTO]")[1].split("[TAGS]")[0].strip()
            tags = raw.split("[TAGS]")[1].split("[FIM]")[0].strip()
        except: manchete, materia, sentimento, tags = entry.title, entry.get('summary', ''), "Neutro", "Geral"
        
        id_noticia = str(int(time.time() * 1000) + hash(cat + entry.title))
        img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
        if 'media_content' in entry: img = entry.media_content[0].get('url', img)
        elif 'links' in entry:
            for l in entry.links:
                if 'image' in l.get('type', ''): img = l.get('href', img)

        gerar_pagina_individual(id_noticia, manchete, materia, img, cat, sentimento, tags)
        tags_h = "".join([f'<span class="tag-item">#{t.strip()}</span>' for t in tags.split(",")])
        
        cards_html += f'''
        <div class="noticia-card" data-id="{id_noticia}" data-categoria="{cat}" onclick="abrirMateria('{id_noticia}')">
            <div class="img-container"><img src="{img}" class="noticia-img"></div>
            <div class="noticia-body">
                <span class="sentiment-tag bg-{sentimento.lower()}">{sentimento}</span>
                <h2>{manchete}</h2>
                <p>{materia[:150]}...</p>
                <div style="margin-bottom:8px;">{tags_h}</div>
                <small class="timeago" datetime="{datetime.now(fuso).isoformat()}"></small> • <a href="materia/{id_noticia}.html" style="font-size:0.8em; color:#d93025; text-decoration:none;" onclick="event.stopPropagation();">Ler mais</a>
            </div>
        </div>
        <div id="modal-{id_noticia}" class="modal">
            <div class="modal-content"><span class="fechar-modal" onclick="fecharMateria('{id_noticia}')">&times;</span>
            <img src="{img}" style="width:100%; border-radius:8px;"><h1>{manchete}</h1><p>{materia.replace(chr(10), '<br><br>')}</p></div>
        </div>'''
        
        adicionadas += 1
        if adicionadas == 3: cards_html += '<div class="ad-slot">🚀 Espaço para Publicidade / Afiliados</div>'
        hist_html += f'<div class="historico-item"><b>{cat}</b><br>{manchete}</div>'
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
    
    filtros = """
    <div class="filter-container">
        <div class="filter-group">
            <button class="filter-btn active" onclick="filtrarNoticias('todas', this)">🏠 Todas</button>
            <button class="filter-btn" onclick="filtrarNoticias('Esquerda', this)">Esquerda</button>
            <button class="filter-btn" onclick="filtrarNoticias('Centro', this)">Centro</button>
            <button class="filter-btn" onclick="filtrarNoticias('Direita', this)">Direita</button>
        </div>
        <div class="filter-group">
            <button class="filter-btn" onclick="filtrarNoticias('Hardware', this)">Hardware</button>
            <button class="filter-btn" onclick="filtrarNoticias('Games', this)">Games</button>
            <button class="filter-btn" onclick="filtrarNoticias('C#', this)">C#</button>
            <button class="filter-btn" onclick="filtrarNoticias('Tech', this)">Tech</button>
            <button class="filter-btn" onclick="filtrarNoticias('Mundo', this)">Mundo</button>
        </div>
    </div>"""

    final = f"<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Portal IA News</title>{CSS}</head><body><header><div class='weather-widget' id='weather-display' onclick='alterarCidade(event)'>⏳</div><h1>Portal IA News</h1></header><div class='search-container'><input type='text' id='search-input' placeholder='O que você quer ler hoje?' onkeyup='pesquisar()'></div>{filtros}<div class='main-wrapper'><div class='content-area'>{novas}{antigas}</div><div class='sidebar'><h3>Últimas Capturas</h3><div class='sidebar-list'>{novos_h}{hist_antigo}</div></div></div>{JS}</body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(final)

if __name__ == "__main__": atualizar_portal()
