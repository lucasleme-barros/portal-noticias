import os
import google.generativeai as genai
import feedparser
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# --- CONFIGURAÇÃO ---
# Puxa o GEMINI_API_KEY que configuramos nos Secrets do seu GitHub
CHAVE_GITHUB = os.environ.get("GEMINI_API_KEY")
if CHAVE_GITHUB:
    genai.configure(api_key=CHAVE_GITHUB)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None
    print("ERRO: GEMINI_API_KEY não configurada!")

fuso = pytz.timezone('America/Sao_Paulo')
agora_str = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

FEEDS = {
    "Mundo": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Tecnologia": "https://br.ign.com/feed.xml"
}

# CSS BLINDADO: Imagens em 16:9 e Modal Ajustado
CSS = """
<style>
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 3px solid #d93025; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    
    .main-wrapper { display: flex; max-width: 1100px; margin: 20px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 10px; }
    
    /* CARD DA HOME - Proporção 16:9 */
    .noticia-card { background: #fff; margin-bottom: 25px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; cursor: pointer; transition: 0.3s; }
    .noticia-card:hover { transform: translateY(-3px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
    
    .noticia-img { 
        width: 100% !important; 
        aspect-ratio: 16 / 9 !important; 
        object-fit: cover !important; 
        display: block;
        max-height: 250px !important; 
    }
    
    .noticia-body { padding: 20px; }
    .noticia-body h2 { margin: 10px 0; font-size: 1.4em; line-height: 1.3; color: #1a73e8; font-weight: bold; }
    .noticia-body p { color: #555; font-size: 0.95em; line-height: 1.5; }
    
    /* MODAL (NOTÍCIA COMPLETA) */
    .modal { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); overflow-y: auto; padding: 20px; }
    .modal-content { background: #fff; margin: 20px auto; padding: 30px; width: 95%; max-width: 800px; border-radius: 12px; position: relative; box-shadow: 0 5px 30px rgba(0,0,0,0.5); }
    .modal-img { width: 100% !important; aspect-ratio: 16 / 9 !important; object-fit: cover !important; border-radius: 8px; margin-bottom: 20px; display: block; }
    
    .fechar-modal { position: absolute; right: 20px; top: 10px; font-size: 40px; cursor: pointer; color: #aaa; font-weight: bold; }
    .sidebar-list { margin-top: 15px; }
    .historico-item { font-size: 0.85em; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; color: #444; }
    .historico-item b { color: #d93025; }
    
    @media (max-width: 800px) { .main-wrapper { flex-direction: column; } .sidebar { position: static; } }
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
// Fecha ao clicar fora do modal
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}
</script>
"""

def processar_noticia(titulo, resumo):
    if model:
        prompt = f"Aja como jornalista. Título: {titulo}. Resumo: {resumo}. Gere: [MANCHETE] (Curta e impactante) [MATERIA] (3 parágrafos detalhados) [FIM]"
        try:
            response = model.generate_content(prompt)
            return response.text
        except: return f"[MANCHETE] {titulo} [MATERIA] {resumo} [FIM]"
    return f"[MANCHETE] {titulo} [MATERIA] {resumo} [FIM]"

def atualizar_portal():
    antigas_noticias = ""
    antigo_historico = ""
    
    # LÓGICA DE PERSISTÊNCIA (VOLUME)
    if os.path.exists("index.html"):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                area_news = soup.find(class_='content-area')
                area_hist = soup.find(class_='sidebar-list')
                if area_news:
                    # Captura cards e modais antigos (limite de 15 para performance)
                    cards = area_news.find_all(lambda tag: tag.name == 'div' and 'noticia-card' in tag.get('class', []))[:15]
                    modais = area_news.find_all(class_='modal')[:15]
                    antigas_noticias = "".join([str(c) for c in cards]) + "".join([str(m) for m in modais])
                if area_hist:
                    itens = area_hist.find_all(class_='historico-item')[:20]
                    antigo_historico = "".join([str(i) for i in itens])
        except Exception as e:
            print(f"Aviso: Erro ao ler histórico: {e}")

    novas_noticias = ""
    novos_historicos = ""
    
    for cat, url in FEEDS.items():
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            texto_ia = processar_noticia(entry.title, entry.summary)
            
            # Parsing do conteúdo da IA
            try:
                manchete = texto_ia.split("[MANCHETE]")[1].split("[MATERIA]")[0].strip()
                materia = texto_ia.split("[MATERIA]")[1].split("[FIM]")[0].strip()
            except:
                manchete, materia = entry.title, entry.summary

            id_noticia = int(time.time() * 1000) + hash(cat)
            
            # Captura de Imagem
            img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
            if 'media_content' in entry: img = entry.media_content[0]['url']

            # GERAÇÃO DO HTML (CARD + MODAL)
            novas_noticias += f'''
            <div class="noticia-card" onclick="abrirMateria('{id_noticia}')">
                <img src="{img}" class="noticia-img">
                <div class="noticia-body">
                    <small style="color:#d93025; font-weight:bold;">{cat.upper()} • {agora_str}</small>
                    <h2>{manchete}</h2>
                    <p style="color:#666; font-size:0.85em;">Clique para ler a matéria completa...</p>
                </div>
            </div>
            
            <div id="modal-{id_noticia}" class="modal">
                <div class="modal-content">
                    <span class="fechar-modal" onclick="fecharMateria('{id_noticia}')">&times;</span>
                    <img src="{img}" class="modal-img">
                    <small style="color:#d93025; font-weight:bold;">{cat.upper()} • {agora_str}</small>
                    <h1 style="margin-top:10px; line-height:1.2; font-size:1.8em;">{manchete}</h1>
                    <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                    <div style="font-size:1.15em; color:#333; line-height:1.6;">{materia.replace(chr(10), '<br><br>')}</div>
                </div>
            </div>
            '''
            novos_historicos += f'<div class="historico-item"><b>{agora_str}</b><br>{manchete}</div>'
            time.sleep(1)

    # MONTAGEM DO ARQUIVO FINAL
    final_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Portal IA News</title>{CSS}</head>
<body>
    <header><h1>Portal IA News</h1><p>Volume de notícias acumulado • Atualizado às {agora_str}</p></header>
    <div class="main-wrapper">
        <div class="content-area">{novas_noticias}{antigas_noticias}</div>
        <div class="sidebar"><h3>Histórico do Dia</h3><div class="sidebar-list">{novos_historicos}{antigo_historico}</div></div>
    </div>
    {JS}
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    print(f"✅ Portal atualizado às {agora_str}!")

if __name__ == "__main__":
    atualizar_portal()
