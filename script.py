import os
import json
import uuid
import html
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
    
    .weather-widget { position: absolute; top: 10px; right: 20px; font-size: 0.85em; color: #555; background: #f9f9f9; padding: 5px 12px; border-radius: 15px; border: 1px solid #eee; cursor: pointer; display: flex; align-items: center; gap: 8px; }
    .weather-city { font-weight: bold; text-decoration: underline; }

    .search-container { padding: 15px; text-align: center; background: #f6f6f6; border-bottom: 1px solid #eee; }
    #search-input { padding: 10px 20px; width: 80%; max-width: 400px; border-radius: 25px; border: 1px solid #ddd; outline: none; }

    .filter-container { padding: 10px; background: #fff; border-bottom: 1px solid #eee; text-align: center; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .filter-group { margin-bottom: 5px; }
    .filter-btn { background: none; border: none; padding: 5px 12px; margin: 2px; cursor: pointer; font-weight: bold; font-size: 0.75em; color: #d93025; text-transform: uppercase; transition: 0.3s; }
    .filter-btn.active { background: #d93025; color: #fff; border-radius: 4px; }

    .main-wrapper { max-width: 1300px; margin: 20px auto; padding: 0 20px; display: flex; gap: 30px; }
    .content-area { flex: 3; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 25px; align-content: start; }

    .noticia-card { background: #fff; padding-bottom: 20px; cursor: pointer; transition: 0.3s; position: relative; border-bottom: 1px solid #f0f0f0; display: flex; flex-direction: column; text-decoration: none; color: inherit; }
    .noticia-card:hover { opacity: 0.8; }
    
    .sentiment-tag { font-size: 0.65em; font-weight: bold; text-transform: uppercase; padding: 2px 6px; border-radius: 3px; margin-bottom: 8px; display: inline-block; color: #fff; width: fit-content; }
    .bg-positivo { background: #28a745; } .bg-negativo { background: #dc3545; } .bg-neutro { background: #6c757d; }

    .img-container { width: 100%; aspect-ratio: 16/9; background: #f8f8f8; border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
    .noticia-img { width: 100%; height: 100%; object-fit: cover; }
    
    .noticia-body h2 { margin: 0; font-size: 1.2em; line-height: 1.25; font-weight: 700; color: #111; }
    .noticia-body p { font-size: 0.9em; color: #555; margin: 10px 0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.4; }
    
    .tag-item { font-size: 0.7em; color: #d93025; font-weight: bold; margin-right: 8px; }
    .sidebar { flex: 1; border-left: 1px solid #eee; padding-left: 20px; max-width: 300px; }
    .sidebar h3 { font-size: 0.85em; text-transform: uppercase; color: #d93025; border-bottom: 2px solid #d93025; display: inline-block; margin-bottom: 15px; }
    .historico-item { font-size: 0.85em; margin-bottom: 15px; border-bottom: 1px solid #f6f6f6; padding-bottom: 10px; }

    @media (max-width: 900px) { .main-wrapper { flex-direction: column; } .content-area { grid-template-columns: 1fr; } .sidebar { border-left: none; padding-left: 0; } }
</style>
"""

JS = """
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

    function filtrarNoticias(cat, btn) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.noticia-card').forEach(c => {
            const cardCat = c.getAttribute('data-categoria').toLowerCase();
            c.style.display = (cat === 'todas' || cardCat.includes(cat.toLowerCase())) ? 'flex' : 'none';
        });
    }

    window.onload = () => { carregarClima(); timeago().render(document.querySelectorAll('.timeago'), 'pt_BR'); };
</script>
"""

def processar_noticia_ai(titulo, resumo, categoria):
    if not model: return None
    prompt = f"""Analista G1. Categoria: {categoria}. Titulo: {titulo}. Contexto: {resumo}.
    Responda EXCLUSIVAMENTE um JSON:
    {{
        "manchete": "string curta",
        "materia": "string 3 parágrafos",
        "sentimento": "Positivo|Negativo|Neutro",
        "tags": "tag1, tag2"
    }}"""
    try:
        res = model.generate_content(prompt)
        clean = res.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean)
    except: return None

def gerar_pagina_individual(id_noticia, data, cat):
    os.makedirs("materia", exist_ok=True)
    m_esc = html.escape(data['manchete'])
    mat_esc = html.escape(data['materia']).replace(chr(10), '<br><br>')
    
    html_content = f"""<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>{m_esc}</title>{CSS}</head>
    <body style='padding:20px; max-width:800px; margin:auto;'>
        <header><a href='../index.html' style='color:#d93025; font-weight:bold; text-decoration:none;'>← VOLTAR</a></header>
        <article style='margin-top:30px;'>
            <img src='{data['img']}' style='width:100%; border-radius:12px;'>
            <h1 style='font-size:2.5em;'>{m_esc}</h1>
            <p style='font-size:1.2em; line-height:1.6; color:#333;'>{mat_esc}</p>
            <hr><small>Categoria: {cat} | Tags: {data['tags']}</small>
        </article>
    </body></html>"""
    with open(f"materia/{id_noticia}.html", "w", encoding="utf-8") as f: f.write(html_content)

def extrair_noticias_da_fonte(item):
    cat, url = item
    feed = feedparser.parse(url)
    cards_html, hist_html = "", ""
    for entry in feed.entries[:5]:
        data = processar_noticia_ai(entry.title, entry.get('summary', ''), cat)
        if not data: continue

        id_noticia = str(uuid.uuid4())
        img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
        if 'media_content' in entry: img = entry.media_content[0]['url']
        data['img'] = img

        gerar_pagina_individual(id_noticia, data, cat)
        
        m_esc = html.escape(data['manchete'])
        tags_h = "".join([f'<span class="tag-item">#{t.strip()}</span>' for t in data['tags'].split(",")])
        
        cards_html += f'''
       <a href="./materia/{id_noticia}.html" class="noticia-card" data-categoria="{cat}">
            <div class="img-container"><img src="{img}" class="noticia-img"></div>
            <div class="noticia-body">
                <span class="sentiment-tag bg-{data['sentimento'].lower()}">{data['sentimento']}</span>
                <h2>{m_esc}</h2>
                <p>{html.escape(data['materia'][:130])}...</p>
                <div>{tags_h}</div>
                <small class="timeago" datetime="{datetime.now(fuso).isoformat()}"></small>
            </div>
        </a>'''
        hist_html += f'<div class="historico-item"><b>{cat}</b><br>{m_esc}</div>'
    return cards_html, hist_html

def atualizar_portal():
    antigas, hist_antigo = "", ""
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            antigas = "".join([str(c) for c in soup.find_all(class_='noticia-card')[:40]])
            hist_antigo = "".join([str(i) for i in soup.find_all(class_='historico-item')[:50]])

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

  final = f"<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Portal IA News</title>{CSS}</head><body><header><div class='weather-widget' id='weather-display' onclick='alterarCidade(event)'>⏳</div><h1>Portal IA News</h1></header>{filtros}<div class='main-wrapper'><div class='content-area'>{novas}{antigas}</div><div class='sidebar'><h3>Histórico</h3><div class='sidebar-list'>{novos_h}{hist_antigo}</div></div></div>{JS}</body></html>"
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final)

    # CORREÇÃO: Estas linhas precisam estar dentro da função (recuadas)
    with open(".nojekyll", "w") as f:
        f.write("")

if __name__ == "__main__": 
    atualizar_portal()
