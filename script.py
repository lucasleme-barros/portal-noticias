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

# --- DICIONÁRIO DE FEEDS ---
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

# --- CSS & JS (Constantes para organização) ---
CSS_STYLE = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #fff; margin: 0; color: #333; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 1px solid #eee; position: relative; }
    .weather-widget { position: absolute; top: 10px; right: 20px; font-size: 0.85em; color: #555; cursor: pointer; }
    .filter-container { padding: 10px; background: #fff; border-bottom: 1px solid #eee; text-align: center; position: sticky; top: 0; z-index: 100; }
    .filter-btn { background: none; border: none; padding: 5px 12px; cursor: pointer; font-weight: bold; font-size: 0.75em; color: #d93025; text-transform: uppercase; }
    .filter-btn.active { background: #d93025; color: #fff; border-radius: 4px; }
    .content-area { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 25px; padding: 20px; max-width: 1200px; margin: auto; }
    .noticia-card { border-bottom: 1px solid #f0f0f0; padding-bottom: 15px; cursor: pointer; text-decoration: none; color: inherit; display: flex; flex-direction: column; }
    .img-container { width: 100%; aspect-ratio: 16/9; border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
    .noticia-img { width: 100%; height: 100%; object-fit: cover; }
    .sentiment-tag { font-size: 0.6em; font-weight: bold; text-transform: uppercase; padding: 2px 6px; border-radius: 3px; color: #fff; width: fit-content; margin-bottom: 5px; }
    .bg-positivo { background: #28a745; } .bg-negativo { background: #dc3545; } .bg-neutro { background: #6c757d; }
    h2 { font-size: 1.2em; line-height: 1.2; margin: 5px 0; }
    p { font-size: 0.9em; color: #666; -webkit-line-clamp: 3; display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; }
</style>
"""

# --- FUNÇÕES DE APOIO ---

def get_existing_titles():
    """Lê o index atual para evitar processar notícias repetidas (Economia de API)"""
    titles = set()
    if os.path.exists("index.html"):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                for h2 in soup.find_all('h2'):
                    titles.add(h2.text.strip())
        except: pass
    return titles

def processar_noticia_ai(titulo, resumo, categoria):
    """Solicita JSON da IA para maior robustez e segurança"""
    if not model: return None
    
    prompt = f"""
    Aja como jornalista. Analise: Título: {titulo}, Contexto: {resumo}.
    Responda EXCLUSIVAMENTE um JSON com este formato:
    {{
        "manchete": "string",
        "materia": "string (3 parágrafos)",
        "sentimento": "Positivo|Negativo|Neutro",
        "tags": "tag1, tag2, tag3"
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Limpeza básica caso a IA coloque blocos de código ```json
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_json)
    except Exception as e:
        print(f"Erro IA: {e}")
        return None

def gerar_pagina_individual(id_noticia, data):
    """Gera página individual com escape de HTML e Meta Tags de SEO"""
    os.makedirs("materia", exist_ok=True)
    
    # Sanitização contra XSS
    m_esc = html.escape(data['manchete'])
    c_esc = html.escape(data['materia'])
    
    html_content = f"""
    <!DOCTYPE html><html lang='pt-BR'><head>
    <meta charset='UTF-8'>
    <title>{m_esc}</title>
    <meta name="description" content="{c_esc[:150]}">
    <meta property="og:title" content="{m_esc}">
    <meta property="og:image" content="{data['img']}">
    {CSS_STYLE}
    </head>
    <body style="padding:20px; max-width:800px; margin:auto;">
        <header><a href='../index.html'>← VOLTAR</a></header>
        <article>
            <img src='{data['img']}' style='width:100%; border-radius:12px;'>
            <h1>{m_esc}</h1>
            <p style='font-size:1.2em; line-height:1.6;'>{c_esc.replace(chr(10), '<br><br>')}</p>
        </article>
    </body></html>
    """
    with open(f"materia/{id_noticia}.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def extrair_noticias_da_fonte(item):
    cat, url = item
    feed = feedparser.parse(url)
    cards_html = ""
    existentes = get_existing_titles()
    
    for entry in feed.entries[:5]:
        if entry.title.strip() in existentes: continue
        
        data_ia = processar_noticia_ai(entry.title, entry.get('summary', ''), cat)
        if not data_ia: continue

        id_noticia = str(uuid.uuid4())
        img = entry.media_content[0]['url'] if 'media_content' in entry else "[https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800](https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800)"
        data_ia['img'] = img

        gerar_pagina_individual(id_noticia, data_ia)

        # Sanitização para o card
        m_esc = html.escape(data_ia['manchete'])
        
        cards_html += f'''
        <a href="materia/{id_noticia}.html" class="noticia-card" data-categoria="{cat}">
            <div class="img-container"><img src="{img}" class="noticia-img"></div>
            <div class="sentiment-tag bg-{data_ia['sentimento'].lower()}">{data_ia['sentimento']}</div>
            <h2>{m_esc}</h2>
            <p>{html.escape(data_ia['materia'][:120])}...</p>
        </a>
        '''
    return cards_html

def atualizar_portal():
    # Coleta de conteúdo antigo para persistência
    antigos = ""
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            antigos = "".join([str(c) for c in soup.find_all(class_='noticia-card')[:50]])

    with ThreadPoolExecutor(max_workers=10) as ex:
        resultados = list(ex.map(extrair_noticias_da_fonte, FEEDS.items()))

    novas = "".join(resultados)
    
    # Layout Final
    filtros = """
    <div class="filter-container">
        <button class="filter-btn active" onclick="filtrar('todas')">Todas</button>
        <button class="filter-btn" onclick="filtrar('Hardware')">Hardware</button>
        <button class="filter-btn" onclick="filtrar('Cyber')">Cyber</button>
        <button class="filter-btn" onclick="filtrar('C#')">C#</button>
    </div>
    """

    final_html = f"""
    <!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'>{CSS_STYLE}</head>
    <body>
        <header><h1>Portal IA News</h1></header>
        {filtros}
        <div class="content-area">{novas}{antigos}</div>
        <script>
            function filtrar(cat) {{
                document.querySelectorAll('.noticia-card').forEach(c => {{
                    c.style.display = (cat === 'todas' || c.dataset.categoria.includes(cat)) ? 'flex' : 'none';
                }});
            }}
        </script>
    </body></html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    atualizar_portal()
