import os
import google.generativeai as genai
import feedparser
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAÇÃO INICIAL ---
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
    "Mundo_DW": "https://rss.dw.com/rdf/rss-br-top",
    "Mundo_ElPais": "https://brasil.elpais.com/rss/brasil/portada.xml",
    "Mundo_RFI": "https://www.portugues.rfi.fr/geral/rss",
    "Esportes_GE": "https://ge.globo.com/rss/ge/",
    "Esportes_ESPN": "https://www.espn.com.br/rss/noticias",
    "Esportes_UOL": "https://noticias.uol.com.br/esporte/index.xml",
    "Esportes_Lance": "https://www.lance.com.br/rss/index.xml",
    "Esportes_Gazeta": "https://www.gazetaesportiva.com/feed/",
    "Games_IGN": "https://br.ign.com/feed.xml",
    "Games_Eurogamer": "https://www.eurogamer.pt/rss",
    "Games_Voxel": "https://www.voxel.com.br/rss",
    "Games_TheEnemy": "https://www.theenemy.com.br/rss",
    "Games_GameSpot": "https://www.gamespot.com/feeds/news/",
    "Hardware_Adrenaline": "https://www.adrenaline.com.br/feed/",
    "Hardware_TechPowerUp": "https://www.techpowerup.com/rss/news",
    "Hardware_Toms": "https://www.tomshardware.com/rss.xml",
    "Hardware_Guru3D": "https://www.guru3d.com/index.php?ct=news&action=rss",
    "Hardware_Wccftech": "https://wccftech.com/category/hardware/feed/",
    "Tech_G1": "https://g1.globo.com/rss/g1/tecnologia/",
    "Tech_Crunch": "https://techcrunch.com/feed/",
    "Tech_Wired": "https://www.wired.com/feed/rss",
    "Tech_Gizmodo": "https://gizmodo.uol.com.br/feed/",
    "Tech_OlharDigital": "https://olhardigital.com.br/feed/",
    "C#_MS_Blog": "https://devblogs.microsoft.com/dotnet/feed/",
    "C#_Corner": "https://www.c-sharpcorner.com/rss/news",
    "C#_AndrewLock": "https://andrewlock.net/rss.xml",
    "C#_DZone": "https://dzone.com/feeds/zones/dotnet.rss",
    "C#_MS_Setup": "https://devblogs.microsoft.com/setup/feed/",
    "Dev_InfoQ": "https://www.infoq.com/br/feed/",
    "Dev_TabNews": "https://www.tabnews.com.br/recentes/rss",
    "Dev_BrazilJS": "https://braziljs.org/rss/",
    "Dev_Alura": "https://www.alura.com.br/artigos/rss",
    "Dev_Medium": "https://medium.com/feed/tag/programação",
    "Cyber_CISO": "https://www.cisoadvisor.com.br/rss-feed/",
    "Cyber_HackerNews": "https://feeds.feedburner.com/TheHackersNews",
    "Cyber_DarkReading": "https://www.darkreading.com/rss.xml",
    "Cyber_WeLiveSecurity": "https://www.welivesecurity.com/br/feed/",
    "Cyber_Krebs": "https://krebsonsecurity.com/feed/",
    "Geral_CNN": "https://www.cnnbrasil.com.br/feed/",
    "Geral_Folha": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
    "Geral_Estadao": "https://www.estadao.com.br/arc/outboundfeeds/rss/categoria/brasil/",
    "Geral_Poder360": "https://www.poder360.com.br/feed/",
    "Geral_Nexo": "https://www.nexojornal.com.br/rss/",
    "Esquerda_247": "https://www.brasil247.com/feed",
    "Esquerda_DCM": "https://www.diariodocentrodomundo.com.br/feed/",
    "Centro_CNN": "https://www.cnnbrasil.com.br/politica/feed/",
    "Centro_G1": "https://g1.globo.com/rss/g1/politica/",
    "Direita_Gazeta": "https://www.gazetadopovo.com.br/feed/rss/rodrigo-constantino.xml",
    "Direita_Oeste": "https://revistaoeste.com/feed/"
}

# (O CSS e o JS permanecem os mesmos da versão anterior)
CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 3px solid #d93025; }
    .filter-container { text-align: center; padding: 15px; position: sticky; top: 0; background: #f0f2f5; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; flex-direction: column; gap: 8px; }
    .filter-btn { background: #fff; border: 2px solid #ddd; padding: 6px 14px; margin: 2px; border-radius: 20px; cursor: pointer; font-weight: bold; transition: 0.3s; font-size: 0.9em; }
    .filter-btn:hover { background: #e8f0fe; border-color: #1a73e8; }
    .filter-btn.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }
    .main-wrapper { display: flex; max-width: 1250px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1.2; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 150px; }
    .noticia-card { background: #fff; margin-bottom: 30px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; cursor: pointer; }
    .border-esquerda { border-left: 10px solid #d93025 !important; }
    .border-direita { border-left: 10px solid #1a73e8 !important; }
    .border-centro { border-left: 10px solid #6c757d !important; }
    .border-padrao { border-left: 10px solid #00c853; }
    .img-container { position: relative; width: 100%; padding-top: 56.25%; background: #eee; }
    .noticia-img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
    .noticia-body { padding: 20px; }
    .noticia-body h2 { margin: 10px 0; font-size: 1.4em; color: #1a73e8; line-height: 1.2; }
    .modal { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); overflow-y: auto; }
    .modal-content { background: #fff; margin: 30px auto; padding: 30px; width: 90%; max-width: 750px; border-radius: 12px; position: relative; line-height: 1.6; }
    .fechar-modal { position: absolute; right: 20px; top: 10px; font-size: 35px; cursor: pointer; color: #aaa; }
    .historico-item { font-size: 0.85em; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    @media (max-width: 800px) { .main-wrapper { flex-direction: column; } .sidebar { position: static; } }
</style>
"""

JS = """
<script>
function abrirMateria(id) { document.getElementById('modal-' + id).style.display = 'block'; document.body.style.overflow = 'hidden'; }
function fecharMateria(id) { document.getElementById('modal-' + id).style.display = 'none'; document.body.style.overflow = 'auto'; }
function filtrarNoticias(categoria, btn) {
    const cards = document.querySelectorAll('.noticia-card');
    const botoes = document.querySelectorAll('.filter-btn');
    botoes.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    cards.forEach(card => {
        const cardCat = card.getAttribute('data-categoria').toLowerCase();
        const filtro = categoria.toLowerCase();
        card.style.display = (filtro === 'todas' || cardCat.includes(filtro)) ? 'block' : 'none';
    });
}
</script>
"""

def processar_noticia(titulo, resumo, categoria):
    if not model: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [FIM]"
    prompt = f"Jornalista. Cat: {categoria}. Título: {titulo}. Resumo: {resumo}. Gere: [MANCHETE] (Curta) [MATERIA] (3 parágrafos) [FIM]"
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [FIM]"

# FUNÇÃO PARA PROCESSAR CADA FONTE EM PARALELO
def extrair_noticias_da_fonte(item):
    cat, url = item
    print(f"Buscando: {cat}")
    feed = feedparser.parse(url)
    html_cards = ""
    historico_items = ""
    adicionadas = 0
    
    for entry in feed.entries:
        if adicionadas >= 5: break
        
        texto_ia = processar_noticia(entry.title, entry.get('summary', ''), cat)
        
        # Lógica de cor
        classe_cor = "border-padrao"
        if "Esquerda" in cat: classe_cor = "border-esquerda"
        elif "Direita" in cat: classe_cor = "border-direita"
        elif "Centro" in cat: classe_cor = "border-centro"

        try:
            manchete = texto_ia.split("[MANCHETE]")[1].split("[MATERIA]")[0].strip()
            materia = texto_ia.split("[MATERIA]")[1].split("[FIM]")[0].strip()
        except:
            manchete, materia = entry.title, entry.get('summary', '')

        id_noticia = int(time.time() * 1000) + hash(cat + entry.title)
        
        # Imagem robusta
        img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
        try:
            if 'media_content' in entry and len(entry.media_content) > 0:
                img = entry.media_content[0].get('url', img)
            elif 'links' in entry:
                for link in entry.links:
                    if 'image' in link.get('type', ''): img = link.get('href', img)
        except: pass

        html_cards += f'''
        <div class="noticia-card {classe_cor}" data-categoria="{cat}" onclick="abrirMateria('{id_noticia}')">
            <div class="img-container"><img src="{img}" class="noticia-img"></div>
            <div class="noticia-body">
                <small style="color:#666; font-weight:bold;">{cat.upper()} • {agora_str}</small>
                <h2>{manchete}</h2>
            </div>
        </div>
        <div id="modal-{id_noticia}" class="modal">
            <div class="modal-content">
                <span class="fechar-modal" onclick="fecharMateria('{id_noticia}')">&times;</span>
                <div class="img-container" style="margin-bottom:20px;"><img src="{img}" class="noticia-img"></div>
                <h1>{manchete}</h1>
                <div style="font-size:1.1em; color:#333;">{materia.replace(chr(10), '<br><br>')}</div>
            </div>
        </div>
        '''
        historico_items += f'<div class="historico-item"><b>{cat}</b>: {manchete}</div>'
        adicionadas += 1
        time.sleep(0.5) # Delay menor já que as threads dividem o trabalho

    return html_cards, historico_items

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
                    cards = area_news.find_all(class_='noticia-card')[:40]
                    modais = area_news.find_all(class_='modal')[:40]
                    antigas_noticias = "".join([str(c) for c in cards]) + "".join([str(m) for m in modais])
                if area_hist:
                    itens = area_hist.find_all(class_='historico-item')[:50]
                    antigo_historico = "".join([str(i) for i in itens])
        except: pass

    # --- EXECUTANDO EM PARALELO ---
    # Usamos 10 trabalhadores para processar os sites ao mesmo tempo
    with ThreadPoolExecutor(max_workers=10) as executor:
        resultados = list(executor.map(extrair_noticias_da_fonte, FEEDS.items()))

    novas_noticias = "".join([r[0] for r in resultados])
    novos_historicos = "".join([r[1] for r in resultados])

    botoes_filtro = """
    <div class="filter-container">
        <div><button class="filter-btn active" onclick="filtrarNoticias('todas', this)">🏠 Todas</button></div>
        <div>
            <small><b>POLÍTICA:</b></small>
            <button class="filter-btn" style="border-color:#d93025" onclick="filtrarNoticias('Esquerda', this)">Esquerda</button>
            <button class="filter-btn" style="border-color:#6c757d" onclick="filtrarNoticias('Centro', this)">Centro</button>
            <button class="filter-btn" style="border-color:#1a73e8" onclick="filtrarNoticias('Direita', this)">Direita</button>
        </div>
        <div>
            <small><b>TEMAS:</b></small>
            <button class="filter-btn" onclick="filtrarNoticias('Hardware', this)">💻 Hardware</button>
            <button class="filter-btn" onclick="filtrarNoticias('Games', this)">🎮 Games</button>
            <button class="filter-btn" onclick="filtrarNoticias('C#', this)">🎯 C#</button>
            <button class="filter-btn" onclick="filtrarNoticias('Cyber', this)">🛡️ Cyber</button>
            <button class="filter-btn" onclick="filtrarNoticias('Tech', this)">🚀 Tech</button>
            <button class="filter-btn" onclick="filtrarNoticias('Esportes', this)">⚽ Esportes</button>
            <button class="filter-btn" onclick="filtrarNoticias('Mundo', this)">🌎 Mundo</button>
        </div>
    </div>
    """

    final_html = f"<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Portal IA</title>{CSS}</head><body><header><h1>Portal IA News</h1></header>{botoes_filtro}<div class='main-wrapper'><div class='content-area'>{novas_noticias}{antigas_noticias}</div><div class='sidebar'><h3>Histórico</h3><div class='sidebar-list'>{novos_historicos}{antigo_historico}</div></div></div>{JS}</body></html>"
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    atualizar_portal()
