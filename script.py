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
    "Direita_Oeste": "https://revistaoeste.com/feed/"
}

CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #fff; margin: 0; color: #333; }
    header { background: #fff; padding: 20px; text-align: center; border-bottom: 1px solid #eee; position: relative; }
    
    .weather-widget { position: absolute; top: 10px; right: 20px; font-size: 0.8em; color: #666; cursor: pointer; }
    .search-container { padding: 15px; text-align: center; background: #f6f6f6; }
    #search-input { padding: 8px 15px; width: 60%; max-width: 300px; border-radius: 4px; border: 1px solid #ddd; }

    .filter-container { padding: 10px; background: #fff; border-bottom: 1px solid #eee; text-align: center; position: sticky; top: 0; z-index: 100; }
    .filter-btn { background: none; border: none; padding: 5px 12px; margin: 2px; cursor: pointer; font-weight: bold; font-size: 0.8em; color: #d93025; text-transform: uppercase; }
    .filter-btn.active { background: #d93025; color: #fff; border-radius: 4px; }

    .main-wrapper { max-width: 1200px; margin: 20px auto; padding: 0 20px; display: flex; gap: 30px; }
    
    /* GRID ESTILO G1 */
    .content-area { 
        flex: 3;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 20px;
    }

    .noticia-card { 
        background: #fff; 
        border-bottom: 1px solid #eee; 
        padding-bottom: 15px;
        cursor: pointer; 
        transition: 0.2s;
    }
    .noticia-card:hover h2 { color: #d93025; }
    
    .sentiment-tag { font-size: 0.6em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; display: inline-block; }
    .positivo { color: #28a745; } .negativo { color: #dc3545; } .neutro { color: #6c757d; }

    .img-container { width: 100%; aspect-ratio: 16/9; background: #f0f0f0; border-radius: 8px; overflow: hidden; margin-bottom: 10px; }
    .noticia-img { width: 100%; height: 100%; object-fit: cover; }
    
    .noticia-body h2 { margin: 5px 0; font-size: 1.1em; line-height: 1.2; font-weight: 700; color: #333; }
    .noticia-body p { font-size: 0.85em; color: #666; margin-top: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

    .sidebar { flex: 1; border-left: 1px solid #eee; padding-left: 20px; }
    .sidebar h3 { font-size: 0.9em; text-transform: uppercase; color: #d93025; }
    .historico-item { font-size: 0.8em; margin-bottom: 15px; line-height: 1.4; border-bottom: 1px solid #f9f9f9; padding-bottom: 10px; }

    .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); }
    .modal-content { background: #fff; margin: 5% auto; padding: 30px; width: 90%; max-width: 600px; border-radius: 8px; position: relative; }
    
    @media (max-width: 768px) { .main-wrapper { flex-direction: column; } .content-area { grid-template-columns: 1fr; } }
</style>
"""

JS = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/lunr.js/2.3.9/lunr.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/timeago.js/2.0.2/timeago.min.js"></script>
<script>
    async function carregarClima(cidadeManual = null) {
        const display = document.getElementById('weather-display');
        const cidadeSalva = cidadeManual || localStorage.getItem('user_city');
        try {
            let lat, lon, nomeCidade;
            if (cidadeSalva) {
                const geo = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${cidadeSalva}&count=1&language=pt`).then(r => r.json());
                lat = geo.results[0].latitude; lon = geo.results[0].longitude; nomeCidade = geo.results[0].name;
                localStorage.setItem('user_city', nomeCidade);
            } else {
                const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej));
                lat = pos.coords.latitude; lon = pos.coords.longitude;
                nomeCidade = "Sua Região";
            }
            const w = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`).then(r => r.json());
            display.innerHTML = `📍 ${nomeCidade}: ${Math.round(w.current_weather.temperature)}°C`;
        } catch (e) { display.innerHTML = `📍 Definir Local`; }
    }

    function alterarCidade() {
        const nova = prompt("Cidade:");
        if (nova) carregarClima(nova);
    }

    function filtrarNoticias(cat, btn) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.noticia-card').forEach(card => {
            const cardCat = card.getAttribute('data-categoria').toLowerCase();
            card.style.display = (cat === 'todas' || cardCat.includes(cat.toLowerCase())) ? 'block' : 'none';
        });
    }

    function abrirMateria(id) { document.getElementById('modal-' + id).style.display = 'block'; }
    function fecharMateria(id) { document.getElementById('modal-' + id).style.display = 'none'; }
    window.onclick = function(e) { if (e.target.className === 'modal') e.target.style.display = 'none'; };

    window.onload = () => { carregarClima(); timeago().render(document.querySelectorAll('.timeago'), 'pt_BR'); };
</script>
"""

def processar_noticia(titulo, resumo, categoria):
    if not model: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [SENTIMENTO] Neutro [TAGS] Notícia [FIM]"
    prompt = f"Analista G1. Cat: {categoria}. Título: {titulo}. Resumo: {resumo}. Gere: [MANCHETE] (Curta e forte) [MATERIA] (3 parágrafos curtos) [SENTIMENTO] (Positivo, Negativo ou Neutro) [TAGS] (3 tags) [FIM]"
    try: return model.generate_content(prompt).text
    except: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [SENTIMENTO] Neutro [TAGS] Geral [FIM]"

def gerar_pagina_individual(id_noticia, manchete, materia, img, cat):
    os.makedirs("materia", exist_ok=True)
    html = f"<html><head><meta charset='UTF-8'>{CSS}</head><body style='padding:20px;'><a href='../index.html'>← Voltar</a><h1>{manchete}</h1><img src='{img}' style='width:100%; max-width:800px;'><p>{materia}</p></body></html>"
    with open(f"materia/{id_noticia}.html", "w", encoding="utf-8") as f: f.write(html)

def extrair_noticias_da_fonte(item):
    cat, url = item
    feed = feedparser.parse(url)
    cards_html, hist_html = "", ""
    for entry in feed.entries[:6]:
        raw = processar_noticia(entry.title, entry.get('summary', ''), cat)
        try:
            manchete = raw.split("[MANCHETE]")[1].split("[MATERIA]")[0].strip()
            materia = raw.split("[MATERIA]")[1].split("[SENTIMENTO]")[0].strip()
            sentimento = raw.split("[SENTIMENTO]")[1].split("[TAGS]")[0].strip()
        except: manchete, materia, sentimento = entry.title, entry.get('summary', ''), "Neutro"
        
        id_noticia = str(int(time.time() * 1000) + hash(cat + entry.title))
        img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
        if 'media_content' in entry: img = entry.media_content[0].get('url', img)
        
        gerar_pagina_individual(id_noticia, manchete, materia, img, cat)
        
        cards_html += f'''
        <div class="noticia-card" data-id="{id_noticia}" data-categoria="{cat}" onclick="abrirMateria('{id_noticia}')">
            <div class="img-container"><img src="{img}" class="noticia-img"></div>
            <div class="noticia-body">
                <span class="sentiment-tag {sentimento.lower()}">{sentimento}</span>
                <h2>{manchete}</h2>
                <p>{materia[:100]}...</p>
                <small class="timeago" datetime="{datetime.now(fuso).isoformat()}"></small>
            </div>
        </div>
        <div id="modal-{id_noticia}" class="modal">
            <div class="modal-content"><span style="cursor:pointer; float:right;" onclick="fecharMateria('{id_noticia}')">X</span>
            <img src="{img}" style="width:100%; border-radius:4px;"><h2>{manchete}</h2><p>{materia.replace(chr(10), '<br>')}</p></div>
        </div>'''
        hist_html += f'<div class="historico-item"><b>{cat}</b>: {manchete}</div>'
    return cards_html, hist_html

def atualizar_portal():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            antigas = "".join([str(c) for c in soup.find_all(class_='noticia-card')[:30]])
    else: antigas = ""

    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(extrair_noticias_da_fonte, FEEDS.items()))

    novas = "".join([r[0] for r in res])
    novos_h = "".join([r[1] for r in res])
    
    filtros = """
    <div class="filter-container">
        <button class="filter-btn active" onclick="filtrarNoticias('todas', this)">🏠 Todas</button>
        <button class="filter-btn" onclick="filtrarNoticias('Hardware', this)">Hardware</button>
        <button class="filter-btn" onclick="filtrarNoticias('Games', this)">Games</button>
        <button class="filter-btn" onclick="filtrarNoticias('C#', this)">C#</button>
        <button class="filter-btn" onclick="filtrarNoticias('Esquerda', this)">Esquerda</button>
        <button class="filter-btn" onclick="filtrarNoticias('Direita', this)">Direita</button>
    </div>"""

    final = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><title>IA News</title>{CSS}</head><body><header><div class='weather-widget' id='weather-display' onclick='alterarCidade()'>⏳</div><h1>Portal IA News</h1></header>{filtros}<div class='main-wrapper'><div class='content-area'>{novas}{antigas}</div><div class='sidebar'><h3>Últimas Capturas</h3><div class='sidebar-list'>{novos_h}</div></div></div>{JS}</body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(final)

if __name__ == "__main__": atualizar_portal()
