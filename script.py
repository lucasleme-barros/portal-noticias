import os
import google.generativeai as genai
import feedparser
import time
from datetime import datetime
import pytz

# ==========================================
# 1. CONFIGURAÇÃO (NOME EXATO DO SEU SECRET)
# ==========================================
CHAVE_GITHUB = os.environ.get("GEMINI_API_KEY") # Puxa o GEMINI_API_KEY do seu print

if CHAVE_GITHUB:
    genai.configure(api_key=CHAVE_GITHUB)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None
    print("ERRO: Chave GEMINI_API_KEY não encontrada nos Secrets!")

fuso = pytz.timezone('America/Sao_Paulo')
agora_str = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

FEEDS = {
    "Mundo": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Tecnologia": "https://br.ign.com/feed.xml"
}

# ==========================================
# 2. DESIGN (CSS)
# ==========================================
CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; color: #1c1e21; }
    header { background: #fff; padding: 25px; text-align: center; border-bottom: 3px solid #d93025; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    header h1 { margin: 0; font-size: 2.2em; color: #111; }
    .main-wrapper { display: flex; max-width: 1200px; margin: 25px auto; gap: 20px; padding: 0 20px; }
    .content-area { flex: 3; }
    .sidebar { flex: 1; background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; height: fit-content; position: sticky; top: 10px; }
    .noticia-card { background: #fff; margin-bottom: 25px; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #eee; }
    .noticia-img { width: 100%; height: 280px; object-fit: cover; background: #eee; }
    .noticia-body { padding: 20px; }
    .historico-item { font-size: 0.85em; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    @media (max-width: 850px) { .main-wrapper { flex-direction: column; } .sidebar { position: static; } }
</style>
"""

# ==========================================
# 3. LÓGICA DO PORTAL
# ==========================================
def processar_noticia(titulo, resumo):
    if model:
        prompt = f"Aja como jornalista. Reescreva de forma envolvente em dois parágrafos: Título: {titulo}. Resumo: {resumo}."
        try:
            response = model.generate_content(prompt)
            return response.text
        except:
            return resumo # Fallback se a IA falhar
    return resumo

def atualizar_portal():
    print(f"Iniciando atualização: {agora_str}")
    novas_noticias = ""
    novos_historicos = ""
    
    for cat, url in FEEDS.items():
        print(f"Buscando {cat}...")
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            texto_final = processar_noticia(entry.title, entry.summary)
            
            # Imagem padrão (ou do feed se existir)
            img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
            if 'media_content' in entry: img = entry.media_content[0]['url']
            
            # HTML do Card
            novas_noticias += f'''
            <div class="noticia-card">
                <img src="{img}" class="noticia-img">
                <div class="noticia-body">
                    <small style="color:#d93025; font-weight:bold;">{cat.upper()} • {agora_str}</small>
                    <h2 style="margin: 10px 0;">{entry.title}</h2>
                    <p style="line-height:1.6; color:#444;">{texto_final}</p>
                </div>
            </div>
            '''
            # HTML da Sidebar
            novos_historicos += f'<div class="historico-item"><b>{agora_str}</b><br>{entry.title}</div>'
            time.sleep(1)

    # MONTAGEM FINAL DO HTML
    final_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Portal IA News</title>{CSS}</head>
<body>
    <header><h1>Portal IA News</h1><p>Fluxo Contínuo • Atualizado em {agora_str}</p></header>
    <div class="main-wrapper">
        <div class="content-area">{novas_noticias}</div>
        <div class="sidebar"><h3>Histórico Recente</h3><div class="sidebar-list">{novos_historicos}</div></div>
    </div>
    <footer style="text-align:center; padding:50px; color:#888; font-size:0.8em;">Gerado por IA no GitHub Actions</footer>
</body>
</html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    print("✅ Sucesso! O portal foi reconstruído.")

if __name__ == "__main__":
    atualizar_portal()
