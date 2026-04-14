import os
import json
import uuid
import html
import google.generativeai as genai
import feedparser
import time
import random
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

IMAGENS_BACKUP = [
    "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800",
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800"
]

CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #fff; margin: 0; color: #333; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 1px solid #eee; position: relative; }
    .weather-widget { position: absolute; top: 10px; right: 20px; font-size: 0.85em; color: #555; background: #f9f9f9; padding: 5px 12px; border-radius: 15px; border: 1px solid #eee; cursor: pointer; display: flex; align-items: center; gap: 8px; }
    .filter-container { padding: 10px; background: #fff; border-bottom: 1px solid #eee; text-align: center; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .filter-btn { background: none; border: none; padding: 5px 12px; margin: 2px; cursor: pointer; font-weight: bold; font-size: 0.75em; color: #d93025; text-transform: uppercase; transition: 0.3s; }
    .filter-btn.active { background: #d93025; color: #fff; border-radius: 4px; }
    .main-wrapper { max-width: 1300px; margin: 20px auto; padding: 0 20px; display: flex; gap: 30px; }
    .content-area { flex: 3; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 25px; align-content: start; min-height: 500px; }
    .noticia-card { background: #fff; padding-bottom: 20px; cursor: pointer; transition: 0.3s; position: relative; border-bottom: 1px solid #f0f0f0; display: flex; flex-direction: column; text-decoration: none; color: inherit; }
    .sentiment-tag { font-size: 0.65em; font-weight: bold; text-transform: uppercase; padding: 2px 6px; border-radius: 3px; margin-bottom: 8px; display: inline-block; color: #fff; width: fit-content; }
    .bg-positivo { background: #28a745; } .bg-negativo { background: #dc3545; } .bg-neutro { background: #6c757d; }
    .img-container { width: 100%; aspect-ratio: 16/9; background: #f8f8f8; border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
    .noticia-img { width: 100%; height: 100%; object-fit: cover; }
    .noticia-body h2 { margin: 0; font-size: 1.2em; line-height: 1.25; font-weight: 700; color: #111; }
    .noticia-body p { font-size: 0.9em; color: #555; margin: 10px 0; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.4; }
    .sidebar { flex: 1; border-left: 1px solid #eee; padding-left: 20px; max-width: 300px; }
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
    prompt = f"Analista G1. Cat: {categoria}. Título: {titulo}. Contexto: {resumo}. Responda apenas JSON puro: {{\"manchete\": \"string\", \"materia\": \"string\", \"sentimento\": \"Positivo|Negativo|Neutro\", \"tags\": \"tag\"}}"
    try:
        res = model.generate_content(prompt)
        clean = res.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean)
    except:
        return {"manchete": titulo, "materia": resumo[:300], "sentimento": "Neutro", "tags": "Geral"}

def extrair_noticias(item):
    cat, url = item
    feed = feedparser.parse(url)
    cards, hists = "", ""
    for entry in feed.entries[:3]:
        data = processar_noticia_ai(entry.title, entry.get('summary', ''), cat)
        time.sleep(1.5) # Delay para estabilidade
        
        id_n = str(uuid.uuid4())
        img = entry.media_content[0]['url'] if 'media_content' in entry else random.choice(IMAGENS_BACKUP)
        
        os.makedirs("materia", exist_ok=True)
        m_esc = html.escape(data['manchete'])
        with open(f"materia/{id_n}.html", "w", encoding="utf-8") as f:
            f.write(f"<!DOCTYPE html><html><head><meta charset='UTF-8'>{CSS}</head><body><header><a href='../index.html'>← VOLTAR</a></header><article><h1>{m_esc}</h1><img src='{img}' style='width:100%'><p>{html.escape(data['materia'])}</p></article></body></html>")
        
        cards += f'''<a href="./materia/{id_n}.html" class="noticia-card" data-categoria="{cat}"><div class="img-container"><img src="{img}" class="noticia-img"></div><div class="noticia-body"><span class="sentiment-tag bg-{data['sentimento'].lower()}">{data['sentimento']}</span><h2>{m_esc}</h2><p>{html.escape(data['materia'][:120])}...</p><small class="timeago" datetime="{datetime.now(fuso).isoformat()}"></small></div></a>'''
        hists += f'<div class="historico-item"><b>{cat}</b>: {m_esc}</div>'
    return cards, hists

def atualizar_portal():
    with ThreadPoolExecutor(max_workers=5) as ex:
        resultados = list(ex.map(extrair_noticias, FEEDS.items()))
    
    todas_novas = "".join([r[0] for r in resultados])
    todos_hists = "".join([r[1] for r in resultados])
    
    filtros = """<div class="filter-container"><div class="filter-group"><button class="filter-btn active" onclick="filtrarNoticias('todas', this)">🏠 Todas</button><button class="filter-btn" onclick="filtrarNoticias('Esquerda', this)">Esquerda</button><button class="filter-btn" onclick="filtrarNoticias('Centro', this)">Centro</button><button class="filter-btn" onclick="filtrarNoticias('Direita', this)">Direita</button></div><div class="filter-group"><button class="filter-btn" onclick="filtrarNoticias('Hardware', this)">Hardware</button><button class="filter-btn" onclick="filtrarNoticias('Games', this)">Games</button><button class="filter-btn" onclick="filtrarNoticias('C#', this)">C#</button><button class="filter-btn" onclick="filtrarNoticias('Tech', this)">Tech</button><button class="filter-btn" onclick="filtrarNoticias('Mundo', this)">Mundo</button></div></div>"""
    
    html_final = f"""<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Portal IA News</title>{CSS}</head><body><header><div class='weather-widget' id='weather-display' onclick='alterarCidade(event)'>⏳</div><h1>Portal IA News</h1></header>{filtros}<div class='main-wrapper'><div class='content-area'>{todas_novas}</div><div class='sidebar'><h3>Histórico</h3><div class='sidebar-list'>{todos_hists}</div></div></div>{JS}</body></html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_final)
    with open(".nojekyll", "w") as f:
        f.write("")

if __name__ == "__main__":
    atualizar_portal()
