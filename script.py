import os
from google import genai
import feedparser
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# ==========================================
# 1. CONFIGURAÇÕES E CHAVE
# ==========================================
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)

fuso = pytz.timezone('America/Sao_Paulo')
agora_str = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

FEEDS = {
    "Mundo": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Tecnologia": "https://br.ign.com/feed.xml"
}

# ==========================================
# 2. ESTILO CSS (Design de Duas Colunas)
# ==========================================
CSS = """
<style>
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 30px; text-align: center; border-bottom: 3px solid #d93025; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    header h1 { margin: 0; font-size: 2.2em; color: #111; }
    
    .main-wrapper { display: flex; max-width: 1250px; margin: 30px auto; gap: 25px; padding: 0 20px; }
    
    /* Coluna de Notícias Principais */
    .content-area { flex: 3; }
    .noticia-card { background: #fff; margin-bottom: 30px; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 8px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; }
    .noticia-img { width: 100%; height: 300px; object-fit: cover; background: #ddd; }
    .noticia-body { padding: 25px; }
    .noticia-body small { color: #d93025; font-weight: bold; text-transform: uppercase; font-size: 0.8em; }
    .noticia-body h2 { margin: 10px 0; font-size: 1.6em; line-height: 1.3; }
    .noticia-body p { line-height: 1.6; color: #4b4f56; font-size: 1.05em; }
    
    /* Barra Lateral de Histórico */
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 12px; height: fit-content; position: sticky; top: 20px; border: 1px solid #e0e0e0; }
    .sidebar h3 { border-bottom: 2px solid #1a73e8; padding-bottom: 10px; font-size: 1.1em; margin-top: 0; }
    .historico-item { font-size: 0.9em; margin-bottom: 15px; border-bottom: 1px solid #f0f2f5; padding-bottom: 10px; }
    .historico-item b { color: #1a73e8; display: block; font-size: 0.75em; }
    
    @media (max-width: 900px) { 
        .main-wrapper { flex-direction: column; } 
        .sidebar { position: static; } 
    }
</style>
"""

# ==========================================
# 3. LÓGICA DO ROBÔ
# ==========================================

def processar_noticia(titulo, resumo):
    prompt = f"Resuma como jornalista: Título: {titulo}. Resumo original: {resumo}. Retorne no formato: [RESUMO] (Título chamativo) [MATERIA] (Texto com 2 parágrafos) [FIM]"
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return response.text
    except:
        return None

def gerar_html_noticia(texto_ia, img_url, id_noticia):
    try:
        resumo = texto_ia.split("[RESUMO]")[1].split("[MATERIA]")[0].strip()
        materia = texto_ia.split("[MATERIA]")[1].split("[FIM]")[0].strip()
        
        card_html = f'''
        <div class="noticia-card" id="news-{id_noticia}">
            <img src="{img_url}" class="noticia-img" onerror="this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800'">
            <div class="noticia-body">
                <small>{agora_str}</small>
                <h2>{resumo}</h2>
                <p>{materia.replace(chr(10), '<br>')}</p>
            </div>
        </div>
        '''
        return card_html, resumo
    except:
        return "", ""

def atualizar_portal():
    print(f"Iniciando atualização: {agora_str}")
    
    # Tenta ler o conteúdo anterior para manter o volume de notícias
    antigas_noticias = ""
    antigo_historico = ""
    
    if os.path.exists("index.html"):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                area_noticias = soup.find(class_='content-area')
                area_sidebar = soup.find(class_='sidebar-list')
                
                if area_noticias:
                    antigas_noticias = "".join([str(c) for c in area_noticias.contents])
                if area_sidebar:
                    antigo_historico = "".join([str(c) for c in area_sidebar.contents])
        except Exception as e:
            print(f"Aviso: Não foi possível ler histórico antigo: {e}")

    novas_noticias_bloco = ""
    novos_itens_sidebar = ""
    
    # Processa os feeds (limitado a 1 notícia nova por categoria por vez para não estourar a API)
    for cat, url in FEEDS.items():
        print(f"Verificando {cat}...")
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            # Tenta pegar imagem, se não houver usa uma genérica
            img = "https://images.unsplash.com/photo-1585829365234-781f75d931f4?w=800"
            if 'media_content' in entry: img = entry.media_content[0]['url']
            
            texto = processar_noticia(entry.title, entry.summary)
            if texto and "[RESUMO]" in texto:
                card, titulo = gerar_html_noticia(texto, img, time.time())
                if card:
                    novas_noticias_bloco += card
                    novos_itens_sidebar += f'<div class="historico-item"><b>{agora_str}</b> {titulo}</div>'
            time.sleep(2)

    # Monta o arquivo final (Novas entram no topo das antigas)
    final_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA News - Fluxo Contínuo</title>
    {CSS}
</head>
<body>
    <header>
        <h1>IA News - Fluxo Contínuo</h1>
        <p>Sistema de Notícias Autônomo • Atualizado em {agora_str}</p>
    </header>
    <div class="main-wrapper">
        <div class="content-area">
            {novas_noticias_bloco}
            {antigas_noticias}
        </div>
        <div class="sidebar">
            <h3>Histórico do Dia</h3>
            <div class="sidebar-list">
                {novos_itens_sidebar}
                {antigo_historico}
            </div>
        </div>
    </div>
    <footer style="text-align:center; padding:40px; color:#888; font-size:0.8em;">
        Portal Gerado Automaticamente via GitHub Actions
    </footer>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    print("✅ Processo concluído com sucesso!")

if __name__ == "__main__":
    atualizar_portal()
