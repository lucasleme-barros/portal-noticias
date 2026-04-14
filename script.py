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
    # MUNDO E GERAL
    "Mundo_BBC": "https://feeds.bbci.co.uk/portuguese/rss.xml",
    "Geral_CNN": "https://www.cnnbrasil.com.br/feed/",
    "Geral_G1": "https://g1.globo.com/rss/g1/",
    
    # TECNOLOGIA E HARDWARE
    "Tech_Gizmodo": "https://gizmodo.uol.com.br/feed/",
    "Hardware_Adrenaline": "https://www.adrenaline.com.br/feed/",
    "Hardware_TechPowerUp": "https://www.techpowerup.com/rss/news",
    
    # PROGRAMAÇÃO E SEGURANÇA
    "C#_MS_Blog": "https://devblogs.microsoft.com/dotnet/feed/",
    "Cyber_CISO": "https://www.cisoadvisor.com.br/rss-feed/",
    "Dev_InfoQ": "https://www.infoq.com/br/feed/",

    # ESPORTES E GAMES
    "Esportes_GE": "https://ge.globo.com/rss/ge/",
    "Games_IGN": "https://br.ign.com/feed.xml",
    
    # POLÍTICA
    "Esquerda_247": "https://www.brasil247.com/feed",
    "Centro_CNN_Pol": "https://www.cnnbrasil.com.br/politica/feed/",
    "Direita_Oeste": "https://revistaoeste.com/feed/"
}

CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 3px solid #d93025; position: relative; }
    .weather-widget { position: absolute; top: 10px; right: 20px; font-size: 0.85em; color: #555; background: #f9f9f9; padding: 5px 12px; border-radius: 15px; border: 1px solid #eee; display: flex; align-items: center; gap: 8px; cursor: pointer; }
    .search-container { padding: 10px; background: #fff; text-align: center; border-bottom: 1px solid #ddd; }
    #search-input { padding: 10px; width: 80%; max-width: 400px; border-radius: 20px; border: 1px solid #ccc; outline: none; }
    .filter-container { text-align: center; padding: 15px; position: sticky; top: 0; background: #f0f2f5; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .filter-group { margin-bottom: 8px; }
    .filter-btn { background: #fff; border: 2px solid #ddd; padding: 6px 14px; margin: 2px; border-radius: 20px; cursor: pointer; font-weight: bold; font-size: 0.82em; transition: 0.3s; }
    .filter-btn.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }
    .main-wrapper { display: flex; max-width: 1250px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1.2; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 200px; }
    .noticia-card { background: #fff; margin-bottom: 25px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; cursor: pointer; position: relative; }
    .sentiment-tag { position: absolute; top: 10px; right: 10px; padding: 4px 8px; border-radius: 4px; font-size: 0.7em; font-weight: bold; color: #fff; z-index: 10; }
    .bg-positivo { background: #28a745; } .bg-negativo { background: #dc3545; } .bg-neutro { background: #6c757d; }
    .border-esquerda { border-left: 8px solid #d93025; } .border-direita { border-left: 8px solid #1a73e8; } .border-centro { border-left: 8px solid #6c757d; } .border-padrao { border-left: 8px solid #00c853; }
    .img-container { position: relative; width: 100%; padding-top: 56.25%; background: #eee; }
    .noticia-img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
    .noticia-body { padding: 15px; }
    .noticia-body h2 { margin: 5px 0; font-size: 1.3em; color: #1a73e8; line-height: 1.3; }
    .tag { background: #eef2f7; color: #5a6d82; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; margin-right: 5px; display: inline-block; margin-top: 5px; }
    .ad-slot { background: #f8f9fa; margin: 20px 0; padding: 15px; border-radius: 8px; border: 1px dashed #ccc; text-align: center; color: #999; font-size: 0.8em; }
    .modal { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); overflow-y: auto; }
    .modal-content { background: #fff; margin: 30px auto; padding: 30px; width: 90%; max-width: 750px; border-radius: 12px; position: relative; line-height: 1.7; }
    .fechar-modal { position: absolute; right: 20px; top: 10px; font-size: 30px; cursor: pointer; }
    @media (max-width: 800px) { .main-wrapper { flex-direction: column; } .weather-widget { position: static; margin-top: 10px; } }
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
                const geoRes = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${cidadeSalva}&count=1&language=pt`);
                const geoData = await geoRes.json();
                lat = geoData.results[0].latitude; lon = geoData.results[0].longitude; nomeCidade = geoData.results[0].name;
                localStorage.setItem('user_city', nomeCidade);
            } else {
                const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej));
                lat = pos.coords.latitude; lon = pos.coords.longitude;
                const revGeo = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`);
                const revData = await revGeo.json();
                nomeCidade = revData.address.city || revData.address.town || "Sua Região";
            }
            const wRes = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
            const wData = await wRes.json();
            display.innerHTML = `<span onclick="alterarCidade(event)" class="weather-city">📍 ${nomeCidade}</span>: <b>${Math.round(wData.current_weather.temperature)}°C</b> ☀️`;
        } catch (e) { display.innerHTML = `<span onclick="alterarCidade(event)">📍 Definir Local</span>`; }
    }

    function alterarCidade(e) {
        e.stopPropagation();
        const nova = prompt("Para qual cidade deseja mudar?");
        if (nova) carregarClima(nova);
    }

    let idx;
    function buildIndex() {
        const cards = document.querySelectorAll('.noticia-card');
        idx = lunr(function () {
            this.field('titulo'); this.field('categoria'); this.ref('id');
            cards.forEach(card => this.add({ id: card.getAttribute('data-id'), titulo: card.querySelector('h2').innerText, categoria: card.getAttribute('data-categoria') }));
        });
    }

    function pesquisar() {
        const query = document.getElementById('search-input').value.toLowerCase();
        const cards = document.querySelectorAll('.noticia-card');
        if (!query) { cards.forEach(c => c.style.display = 'block'); return; }
        const results = idx.search(query).map(r => r.ref);
        cards.forEach(card => card.style.display = results.includes(card.getAttribute('data-id')) ? 'block' : 'none');
    }

    function abrirMateria(id) { document.getElementById('modal-' + id).style.display = 'block'; document.body.style.overflow = 'hidden'; }
    function fecharMateria(id) { document.getElementById('modal-' + id).style.display = 'none'; document.body.style.overflow = 'auto'; }
    window.onclick = function(e) { if (e.target.className === 'modal') fecharMateria(e.target.id.split('-')[1]); };

    function filtrarNoticias(cat, btn) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.noticia-card').forEach(card => {
            const cardCat = card.getAttribute('data-categoria').toLowerCase();
            card.style.display = (cat === 'todas' || cardCat.includes(cat.toLowerCase())) ? 'block' : 'none';
        });
    }

    window.onload = () => { buildIndex(); carregarClima(); timeago().render(document.querySelectorAll('.timeago'), 'pt_BR'); };
</script>
"""

def processar_noticia(titulo, resumo, categoria):
    if not model: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [SENTIMENTO] Neutro [TAGS] Notícia [FIM]"
    prompt = f"""Analista Premium. Cat: {categoria}. Título: {titulo}. Contexto: {resumo}.
    Gere: [MANCHETE] (Título analítico) [MATERIA] (3 parágrafos: Fatos, Por que importa e Impacto Futuro) [SENTIMENTO] (Positivo, Negativo ou Neutro) [TAGS] (3 tags) [FIM]"""
    try: return model.generate_content(prompt).text
    except: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [SENTIMENTO] Neutro [TAGS] Geral [FIM]"

def gerar_pagina_individual(id_noticia, manchete, materia, img, cat, sentimento, tags):
    os.makedirs("materia", exist_ok=True)
    html = f"""<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><meta name="keywords" content="{tags}"><title>{manchete}</title>{CSS}</head>
    <body style="background:#fff;"><header><div style="max-width:800px; margin:auto; display:flex; justify-content:space-between; align-items:center;">
    <a href='../index.html' style="text-decoration:none; color:#d93025; font-weight:bold;">← Voltar</a><span style="font-size:0.8em; color:#666;">Categoria: {cat}</span></div></header>
    <article class='modal-content' style="box-shadow:none; border:1px solid #eee;">
    <img src='{img}' style='width:100%; border-radius:12px;'><div style="margin:20px 0;"><span class="sentiment-tag bg-{sentimento.lower()}">{sentimento}</span></div>
    <h1>{manchete}</h1><div style='font-size:1.15em; color:#333;'>{materia.replace(chr(10), '<br><br>')}</div>
    <div style="margin-top:30px; border-top:1px solid #eee; padding-top:10px;"><small>Tags: {tags}</small></div></article></body></html>"""
    with open(f"materia/{id_noticia}.html", "w", encoding="utf-8") as f: f.write(html)

def extrair_noticias_da_fonte(item):
    cat, url = item
    feed = feedparser.parse(url)
    cards_html, hist_html = "", ""
    adicionadas = 0
    for entry in feed.entries[:5]:
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
        
        gerar_pagina_individual(id_noticia, manchete, materia, img, cat, sentimento, tags)
        tags_h = "".join([f'<span class="tag">#{t.strip()}</span>' for t in tags.split(",")])
        classe_cor = "border-esquerda" if "Esquerda" in cat else "border-direita" if "Direita" in cat else "border-centro" if "Centro" in cat else "border-padrao"
        
        cards_html += f'''
        <div class="noticia-card {classe_cor}" data-id="{id_noticia}" data-categoria="{cat}" onclick="abrirMateria('{id_noticia}')">
            <div class="sentiment-tag bg-{sentimento.lower()}">{sentimento}</div>
            <div class="img-container"><img src="{img}" class="noticia-img"></div>
            <div class="noticia-body">
                <small class="timeago" datetime="{datetime.now(fuso).isoformat()}"></small> • <b>{cat.upper()}</b>
                <h2>{manchete}</h2>
                <div class="tags-list">{tags_h}</div>
                <div style="margin-top:10px;"><a href="materia/{id_noticia}.html" style="font-size:0.8em; color:#1a73e8;" onclick="event.stopPropagation();">Link da Matéria</a></div>
            </div>
        </div>
        <div id="modal-{id_noticia}" class="modal">
            <div class="modal-content"><span class="fechar-modal" onclick="fecharMateria('{id_noticia}')">&times;</span>
            <img src="{img}" style="width:100%; border-radius:8px;"><h1>{manchete}</h1><p>{materia.replace(chr(10), '<br>')}</p></div>
        </div>'''
        adicionadas += 1
        if adicionadas == 3: cards_html += '<div class="ad-slot">🚀 Espaço para Publicidade</div>'
        hist_html += f'<div class="historico-item"><b>{cat}</b>: {manchete}</div>'
    return cards_html, hist_html

def atualizar_portal():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            antigas = "".join([str(c) for c in soup.find_all(class_='noticia-card')[:50]])
            hist_antigo = "".join([str(i) for i in soup.find_all(class_='historico-item')[:60]])
    else: antigas, hist_antigo = "", ""

    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(extrair_noticias_da_fonte, FEEDS.items()))

    novas = "".join([r[0] for r in res]); novos_h = "".join([r[1] for r in res])
    
    filtros = """
    <div class="search-container"><input type="text" id="search-input" placeholder="Pesquisar..." onkeyup="pesquisar()"></div>
    <div class="filter-container">
        <div class="filter-group">
            <button class="filter-btn active" onclick="filtrarNoticias('todas', this)">🏠 Todas</button>
            <button class="filter-btn" style="border-color:#d93025" onclick="filtrarNoticias('Esquerda', this)">🔴 Esquerda</button>
            <button class="filter-btn" style="border-color:#6c757d" onclick="filtrarNoticias('Centro', this)">⚪ Centro</button>
            <button class="filter-btn" style="border-color:#1a73e8" onclick="filtrarNoticias('Direita', this)">🔵 Direita</button>
        </div>
        <div class="filter-group">
            <button class="filter-btn" onclick="filtrarNoticias('Hardware', this)">💻 Hardware</button>
            <button class="filter-btn" onclick="filtrarNoticias('Games', this)">🎮 Games</button>
            <button class="filter-btn" onclick="filtrarNoticias('C#', this)">🎯 C#</button>
            <button class="filter-btn" onclick="filtrarNoticias('Cyber', this)">🛡️ Cyber</button>
            <button class="filter-btn" onclick="filtrarNoticias('Tech', this)">🚀 Tech</button>
            <button class="filter-btn" onclick="filtrarNoticias('Esportes', this)">⚽ Esportes</button>
            <button class="filter-btn" onclick="filtrarNoticias('Mundo', this)">🌎 Mundo</button>
        </div>
    </div>"""

    final = f"<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Portal IA News</title>{CSS}</head><body><header><div class='weather-widget' id='weather-display' onclick='alterarCidade(event)'>⏳</div><h1>Portal IA News</h1></header>{filtros}<div class='main-wrapper'><div class='content-area'>{novas}{antigas}</div><div class='sidebar'><h3>Histórico</h3><div class='sidebar-list'>{novos_h}{hist_antigo}</div></div></div>{JS}</body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(final)

if __name__ == "__main__": atualizar_portal()
