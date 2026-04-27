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
    "Mundo_BBC":           "https://feeds.bbci.co.uk/portuguese/rss.xml",
    "Geral_G1":            "https://g1.globo.com/rss/g1/",
    "Hardware_Adrenaline": "https://www.adrenaline.com.br/feed/",
    "C#_MS_Blog":          "https://devblogs.microsoft.com/dotnet/feed/",
    "Cyber_CISO":          "https://www.cisoadvisor.com.br/rss-feed/",
    "Games_IGN":           "https://br.ign.com/feed.xml",
    "Esquerda_247":        "https://www.brasil247.com/feed",
    "Centro_CNN_Pol":      "https://www.cnnbrasil.com.br/politica/feed/",
    "Direita_Oeste":       "https://revistaoeste.com/feed/",
    "Tech_Gizmodo":        "https://gizmodo.uol.com.br/feed/",
    # Novas categorias
    "Economia_Infomoney":  "https://www.infomoney.com.br/feed/",
    "Saude_G1":            "https://g1.globo.com/rss/g1/ciencia-e-saude/",
    "Esportes_GE":         "https://ge.globo.com/rss/ge/",
    "Entret_CNN":          "https://www.cnnbrasil.com.br/entretenimento/feed/",
}

CATEGORY_LABELS = {
    "Mundo":    "🌍 Mundo",
    "Geral":    "📰 Geral",
    "Hardware": "🖥️ Hardware",
    "C#":       "💻 C#",
    "Cyber":    "🔒 Cyber",
    "Games":    "🎮 Games",
    "Esquerda": "⬅ Esquerda",
    "Centro":   "⚖️ Centro",
    "Direita":  "➡ Direita",
    "Tech":     "⚡ Tech",
    "Economia": "💰 Economia",
    "Saude":    "❤️ Saúde",
    "Esportes": "⚽ Esportes",
    "Entret":   "🎭 Entret.",
}

IMAGENS_BACKUP = [
    "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800",
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800",
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=800",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=800",
    "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=800",
    "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800",
    "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?w=800",
    "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800",
    "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=800",
    "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=800",
    "https://images.unsplash.com/photo-1526256262350-7da7584cf5eb?w=800",
    "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800",
]

CSS = """<style>
:root {
    --bg: #f0f2f5;
    --card-bg: #ffffff;
    --text: #111827;
    --text-muted: #6b7280;
    --border: #e5e7eb;
    --accent: #e63946;
    --header-bg: rgba(255,255,255,0.95);
    --shadow: 0 1px 8px rgba(0,0,0,0.07);
    --shadow-hover: 0 8px 28px rgba(0,0,0,0.15);
}
[data-theme="dark"] {
    --bg: #0f172a;
    --card-bg: #1e293b;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --border: #334155;
    --header-bg: rgba(15,23,42,0.95);
    --shadow: 0 1px 8px rgba(0,0,0,0.3);
    --shadow-hover: 0 8px 28px rgba(0,0,0,0.5);
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); transition: background 0.3s, color 0.3s; min-height: 100vh; }
header { background: var(--header-bg); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 300; height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 28px; }
.logo { display: flex; align-items: center; gap: 10px; text-decoration: none; }
.logo-icon { width: 38px; height: 38px; background: var(--accent); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 900; font-size: 1.2em; flex-shrink: 0; }
.logo-text { font-size: 1.25em; font-weight: 800; color: var(--text); letter-spacing: -0.5px; }
.logo-text em { color: var(--accent); font-style: normal; }
.header-right { display: flex; align-items: center; gap: 12px; }
.weather-widget { font-size: 0.8em; color: var(--text-muted); background: var(--bg); padding: 7px 14px; border-radius: 20px; border: 1px solid var(--border); cursor: pointer; display: flex; align-items: center; gap: 6px; transition: 0.2s; white-space: nowrap; }
.weather-widget:hover { border-color: var(--accent); color: var(--text); }
.theme-btn { background: var(--bg); border: 1px solid var(--border); color: var(--text); width: 38px; height: 38px; border-radius: 50%; cursor: pointer; font-size: 1.05em; transition: 0.2s; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.theme-btn:hover { border-color: var(--accent); }
.filter-bar { background: var(--card-bg); border-bottom: 1px solid var(--border); padding: 10px 28px; display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; position: sticky; top: 64px; z-index: 200; }
.filter-btn { background: transparent; border: 1px solid var(--border); color: var(--text-muted); padding: 5px 14px; border-radius: 20px; cursor: pointer; font-size: 0.76em; font-weight: 600; transition: 0.2s; white-space: nowrap; }
.filter-btn:hover { border-color: var(--accent); color: var(--accent); }
.filter-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.main-wrapper { max-width: 1440px; margin: 24px auto; padding: 0 24px; display: flex; gap: 28px; }
.content-area { flex: 1; min-width: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; align-content: start; }
.noticia-card { background: var(--card-bg); border-radius: 14px; overflow: hidden; border: 1px solid var(--border); box-shadow: var(--shadow); display: flex; flex-direction: column; text-decoration: none; color: inherit; transition: transform 0.22s, box-shadow 0.22s; }
.noticia-card:hover { transform: translateY(-5px); box-shadow: var(--shadow-hover); }
.img-container { width: 100%; aspect-ratio: 16/9; overflow: hidden; background: var(--border); }
.noticia-img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.35s; display: block; }
.noticia-card:hover .noticia-img { transform: scale(1.05); }
.noticia-body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.tags-row { display: flex; gap: 5px; flex-wrap: wrap; }
.cat-tag { font-size: 0.63em; font-weight: 700; text-transform: uppercase; padding: 3px 7px; border-radius: 4px; background: var(--bg); color: var(--text-muted); border: 1px solid var(--border); }
.sentiment-tag { font-size: 0.63em; font-weight: 700; text-transform: uppercase; padding: 3px 7px; border-radius: 4px; color: #fff; }
.bg-positivo { background: #16a34a; }
.bg-negativo { background: #dc2626; }
.bg-neutro { background: #6b7280; }
.noticia-body h2 { font-size: 1em; line-height: 1.4; font-weight: 700; color: var(--text); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.noticia-body p { font-size: 0.82em; color: var(--text-muted); line-height: 1.55; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.card-footer { margin-top: auto; padding-top: 8px; display: flex; justify-content: space-between; align-items: center; }
.timeago { font-size: 0.74em; color: var(--text-muted); }
.read-more-label { font-size: 0.74em; color: var(--accent); font-weight: 700; }
.sidebar { flex: 0 0 270px; }
.sidebar-inner { background: var(--card-bg); border-radius: 14px; border: 1px solid var(--border); padding: 16px; position: sticky; top: 130px; max-height: calc(100vh - 150px); overflow-y: auto; }
.sidebar-inner::-webkit-scrollbar { width: 4px; }
.sidebar-inner::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
.sidebar-inner h3 { font-size: 0.78em; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; color: var(--text-muted); margin-bottom: 12px; padding-bottom: 10px; border-bottom: 2px solid var(--accent); }
.historico-item { padding: 9px 0; border-bottom: 1px solid var(--border); }
.historico-item:last-child { border-bottom: none; }
.historico-item b { font-size: 0.68em; font-weight: 800; text-transform: uppercase; color: var(--accent); display: block; margin-bottom: 3px; }
.historico-item span { font-size: 0.78em; color: var(--text-muted); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
@media (max-width: 1200px) { .sidebar { display: none; } }
@media (max-width: 900px) { .main-wrapper { padding: 0 16px; margin: 16px auto; } .filter-bar, header { padding: 8px 16px; } }
@media (max-width: 600px) { .content-area { grid-template-columns: 1fr; } .logo-text { display: none; } }
</style>"""

CSS_ARTICLE = """<style>
:root { --bg:#f0f2f5; --card-bg:#fff; --text:#111827; --text-muted:#6b7280; --border:#e5e7eb; --accent:#e63946; }
[data-theme="dark"] { --bg:#0f172a; --card-bg:#1e293b; --text:#f1f5f9; --text-muted:#94a3b8; --border:#334155; }
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
.art-header { background: var(--card-bg); border-bottom: 1px solid var(--border); padding: 14px 28px; display: flex; align-items: center; gap: 16px; position: sticky; top: 0; z-index: 10; }
.back-btn { background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 7px 16px; border-radius: 20px; cursor: pointer; font-size: 0.82em; font-weight: 600; text-decoration: none; transition: 0.2s; }
.back-btn:hover { border-color: var(--accent); color: var(--accent); }
.art-logo { font-size: 1em; font-weight: 800; color: var(--accent); }
.art-container { max-width: 760px; margin: 32px auto; padding: 0 24px 60px; }
.art-container h1 { font-size: 1.8em; line-height: 1.3; font-weight: 800; margin-bottom: 20px; }
.art-img { width: 100%; border-radius: 14px; margin-bottom: 24px; aspect-ratio: 16/9; object-fit: cover; }
.art-body { font-size: 1.05em; line-height: 1.75; color: var(--text); }
.art-body p { margin-bottom: 1.4em; }
.fonte-btn { display: inline-block; margin-top: 32px; padding: 12px 24px; background: var(--accent); color: #fff; border-radius: 24px; text-decoration: none; font-weight: 700; font-size: 0.9em; transition: opacity 0.2s; }
.fonte-btn:hover { opacity: 0.85; }
</style>
<script>(function(){ const s=localStorage.getItem('theme'); if(s==='dark') document.documentElement.setAttribute('data-theme','dark'); })();</script>"""

THEME_SCRIPT = """<script>(function(){ const s=localStorage.getItem('theme'); if(s==='dark') document.documentElement.setAttribute('data-theme','dark'); })();</script>"""

JS = """<script src="https://cdnjs.cloudflare.com/ajax/libs/timeago.js/2.0.2/timeago.min.js"></script>
<script>
async function carregarClima(cidadeManual) {
    const display = document.getElementById('weather-display');
    const cidadeSalva = cidadeManual || localStorage.getItem('user_city');
    let lat, lon, nomeCidade;
    try {
        if (cidadeSalva) {
            const geo = await fetch('https://geocoding-api.open-meteo.com/v1/search?name=' + encodeURIComponent(cidadeSalva) + '&count=1&language=pt').then(r => r.json());
            lat = geo.results[0].latitude; lon = geo.results[0].longitude; nomeCidade = geo.results[0].name;
            localStorage.setItem('user_city', nomeCidade);
        } else {
            const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej));
            lat = pos.coords.latitude; lon = pos.coords.longitude;
            const rev = await fetch('https://nominatim.openstreetmap.org/reverse?lat=' + lat + '&lon=' + lon + '&format=json').then(r => r.json());
            nomeCidade = rev.address.city || rev.address.town || 'Sua Cidade';
        }
        const w = await fetch('https://api.open-meteo.com/v1/forecast?latitude=' + lat + '&longitude=' + lon + '&current_weather=true').then(r => r.json());
        display.innerHTML = '<span onclick="alterarCidade(event)">📍 ' + nomeCidade + '</span>: <b>' + Math.round(w.current_weather.temperature) + '°C</b>';
    } catch(e) { display.innerHTML = '<span onclick="alterarCidade(event)">📍 Definir Local</span>'; }
}
function alterarCidade(e) { e.stopPropagation(); const n = prompt('Digite sua cidade:'); if (n) carregarClima(n); }
function toggleTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        document.getElementById('theme-btn').textContent = '🌙';
    } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        document.getElementById('theme-btn').textContent = '☀️';
    }
}
function filtrarNoticias(cat, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    let visiveis = 0;
    document.querySelectorAll('.noticia-card').forEach(c => {
        const cc = (c.getAttribute('data-categoria') || '').toLowerCase();
        const mostrar = cat === 'todas' || cc.includes(cat.toLowerCase());
        c.style.display = mostrar ? '' : 'none';
        if (mostrar) visiveis++;
    });
    let aviso = document.getElementById('sem-resultado');
    if (!aviso) {
        aviso = document.createElement('div');
        aviso.id = 'sem-resultado';
        aviso.style.cssText = 'grid-column:1/-1;text-align:center;padding:60px 20px;color:var(--text-muted);font-size:1em';
        document.querySelector('.content-area').appendChild(aviso);
    }
    aviso.style.display = visiveis === 0 ? 'block' : 'none';
    aviso.textContent = visiveis === 0 ? 'Aguardando próxima atualização automática para esta categoria.' : '';
}
window.addEventListener('DOMContentLoaded', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = isDark ? '☀️' : '🌙';
    carregarClima();
    if (window.timeago) timeago().render(document.querySelectorAll('.timeago'), 'pt_BR');
});
</script>"""

FILTROS = """<div class="filter-bar">
    <button type="button" class="filter-btn active" onclick="filtrarNoticias('todas', this)">🏠 Todas</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Esportes', this)">⚽ Esportes</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Economia', this)">💰 Economia</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Tech', this)">⚡ Tech</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Games', this)">🎮 Games</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Mundo', this)">🌍 Mundo</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Cyber', this)">🔒 Cyber</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Hardware', this)">🖥️ Hardware</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Saude', this)">❤️ Saúde</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Entret', this)">🎭 Entretenimento</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('C#', this)">💻 C#</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Geral', this)">📰 Geral</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Esquerda', this)">⬅ Esquerda</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Centro', this)">⚖️ Centro</button>
    <button type="button" class="filter-btn" onclick="filtrarNoticias('Direita', this)">➡ Direita</button>
</div>"""


def limpar_html(texto):
    if not texto: return ""
    return BeautifulSoup(texto, "html.parser").get_text()

def get_cat_label(cat):
    for key, label in CATEGORY_LABELS.items():
        if key.lower() in cat.lower():
            return label
    return cat.split('_')[0]

def processar_noticia_ai(titulo, resumo, categoria):
    resumo_limpo = limpar_html(resumo)[:600]
    if not model:
        return {"manchete": titulo, "materia": resumo_limpo, "sentimento": "Neutro"}
    prompt = (
        f"Você é um jornalista brasileiro da editoria {categoria}. "
        f"Com base no título e resumo abaixo, escreva uma matéria jornalística completa em português do Brasil.\n"
        f"Título: {titulo}\n"
        f"Resumo: {resumo_limpo}\n\n"
        f"Responda APENAS com JSON puro (sem markdown):\n"
        f'{{\"manchete\": \"título reescrito, impactante, máx 120 caracteres\", '
        f'\"materia\": \"exatamente 3 parágrafos separados por \\n\\n, cada parágrafo com no mínimo 3 frases completas e detalhadas\", '
        f'\"sentimento\": \"Positivo|Negativo|Neutro\"}}'
    )
    try:
        res = model.generate_content(prompt)
        clean = res.text.strip().replace('```json', '').replace('```', '').strip()
        data = json.loads(clean)
        if len(data.get('materia', '')) < 150:
            data['materia'] = resumo_limpo
        return data
    except:
        return {"manchete": titulo, "materia": resumo_limpo, "sentimento": "Neutro"}

def capturar_imagem(entry):
    if 'media_content' in entry: return entry.media_content[0]['url']
    if 'media_thumbnail' in entry: return entry.media_thumbnail[0]['url']
    if 'summary' in entry:
        soup = BeautifulSoup(entry.summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"): return img.get("src")
    return random.choice(IMAGENS_BACKUP)

def gerar_pagina_individual(id_noticia, data, cat, img, fonte_url=""):
    os.makedirs("materia", exist_ok=True)
    m_esc = html.escape(data['manchete'])
    paragrafos = data['materia'].split('\n\n')
    mat_esc = "".join(f"<p>{html.escape(p.strip())}</p>" for p in paragrafos if p.strip())
    fonte_html = (
        f"<a href='{html.escape(fonte_url)}' target='_blank' rel='noopener' class='fonte-btn'>🔗 Ler artigo original</a>"
        if fonte_url else ""
    )
    html_content = (
        "<!DOCTYPE html><html lang='pt-BR'>"
        "<head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{m_esc}</title>{CSS_ARTICLE}</head>"
        "<body>"
        "<div class='art-header'>"
        f"<a href='../index.html' class='back-btn'>← Voltar</a>"
        "<span class='art-logo'>Portal IA News</span>"
        "</div>"
        "<div class='art-container'>"
        f"<h1>{m_esc}</h1>"
        f"<img src='{img}' class='art-img' onerror=\"this.style.display='none'\">"
        f"<div class='art-body'>{mat_esc}</div>"
        f"{fonte_html}"
        "</div></body></html>"
    )
    with open(f"materia/{id_noticia}.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def extrair_noticias(item):
    cat, url = item
    feed = feedparser.parse(url)
    cards, hists = "", ""
    cat_label = get_cat_label(cat)
    for entry in feed.entries[:3]:
        data = processar_noticia_ai(entry.title, entry.get('summary', ''), cat)
        time.sleep(1.5)

        id_n = str(uuid.uuid4())
        img = capturar_imagem(entry)
        fonte_url = entry.get('link', '')
        gerar_pagina_individual(id_n, data, cat, img, fonte_url)

        m_esc = html.escape(data['manchete'])
        mat_preview = html.escape(limpar_html(data['materia'])[:130])
        sentiment = data['sentimento'].lower()
        fallback_img = random.choice(IMAGENS_BACKUP)

        cards += (
            f'\n<a href="./materia/{id_n}.html" class="noticia-card" data-categoria="{cat}">'
            f'<div class="img-container"><img src="{img}" class="noticia-img" loading="lazy" onerror="this.src=\'{fallback_img}\'"></div>'
            f'<div class="noticia-body">'
            f'<div class="tags-row"><span class="cat-tag">{cat_label}</span>'
            f'<span class="sentiment-tag bg-{sentiment}">{data["sentimento"]}</span></div>'
            f'<h2>{m_esc}</h2>'
            f'<p>{mat_preview}...</p>'
            f'<div class="card-footer">'
            f'<small class="timeago" datetime="{datetime.now(fuso).isoformat()}"></small>'
            f'<span class="read-more-label">Ler mais →</span>'
            f'</div></div></a>'
        )
        hists += (
            f'<div class="historico-item">'
            f'<b>{cat_label}</b>'
            f'<span>{m_esc}</span>'
            f'</div>'
        )
    return cards, hists

def atualizar_portal():
    antigas, h_antigo = "", ""
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            antigas = "".join([str(c) for c in soup.find_all(class_='noticia-card')[:30]])
            h_antigo = "".join([str(i) for i in soup.find_all(class_='historico-item')[:30]])

    with ThreadPoolExecutor(max_workers=5) as ex:
        res = list(ex.map(extrair_noticias, FEEDS.items()))

    novas   = "".join([r[0] for r in res])
    novos_h = "".join([r[1] for r in res])

    final = (
        "<!DOCTYPE html><html lang='pt-BR'>"
        "<head>"
        "<meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        "<title>Portal IA News</title>"
        + THEME_SCRIPT
        + CSS +
        "</head><body>"
        "<header>"
        "<a class='logo' href='./'>"
        "<div class='logo-icon'>N</div>"
        "<span class='logo-text'>Portal <em>IA</em> News</span>"
        "</a>"
        "<div class='header-right'>"
        "<div class='weather-widget' id='weather-display'>⏳ Carregando...</div>"
        "<button class='theme-btn' id='theme-btn' onclick='toggleTheme()' title='Alternar tema'>🌙</button>"
        "</div>"
        "</header>"
        + FILTROS +
        "<div class='main-wrapper'>"
        "<div class='content-area'>"
        + novas + antigas +
        "</div>"
        "<div class='sidebar'><div class='sidebar-inner'>"
        "<h3>Histórico</h3>"
        + novos_h + h_antigo +
        "</div></div>"
        "</div>"
        + JS +
        "</body></html>"
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final)
    with open(".nojekyll", "w") as f:
        f.write("")

if __name__ == "__main__":
    atualizar_portal()
