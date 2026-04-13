import os
from google import genai
import feedparser
import time
from datetime import datetime
import pytz

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)

fuso = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso).strftime('%d/%m/%Y %H:%M:%S')

FEEDS = {
    "Mundo & Atualidades": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Games & Tecnologia": "https://br.ign.com/feed.xml"
}

# ==========================================
# 2. TEMPLATE HTML COM MODAL (JANELA DE LEITURA)
# ==========================================
HTML_TEMPLATE_INICIO = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA News Portal</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 0; }}
        header {{ background: #fff; padding: 20px; text-align: center; border-bottom: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        header h1 {{ margin: 0; color: #1a1a1a; text-transform: uppercase; letter-spacing: 1px; }}
        
        .container {{ max-width: 1100px; margin: 30px auto; padding: 0 20px; }}
        .categoria-titulo {{ color: #d32f2f; border-bottom: 2px solid #d32f2f; display: inline-block; padding-bottom: 5px; margin-top: 40px; text-transform: uppercase; font-size: 1.2em; }}
        
        .grid-noticias {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px; }}
        
        .noticia-card {{ background: #fff; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; transition: 0.3s; border: 1px solid #eee; }}
        .noticia-card:hover {{ transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.15); }}
        
        .noticia-img {{ width: 100%; height: 160px; object-fit: cover; }}
        .noticia-content {{ padding: 15px; }}
        .noticia-card h2 {{ margin: 0; font-size: 1.1em; color: #222; line-height: 1.3; height: 3em; overflow: hidden; }}
        
        /* ESTILO DO MODAL (JANELA COMPLETA) */
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); overflow-y: auto; }}
        .modal-content {{ background: #fff; margin: 5% auto; padding: 40px; width: 80%; max-width: 800px; border-radius: 8px; position: relative; line-height: 1.8; }}
        .close-btn {{ position: absolute; right: 20px; top: 10px; font-size: 30px; cursor: pointer; color: #999; }}
        .modal-img {{ width: 100%; max-height: 400px; object-fit: cover; border-radius: 5px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <header>
        <h1>Portal Notícias IA</h1>
        <p style="color: #666; font-size: 0.8em;">Atualizado em: {agora}</p>
    </header>
    <div class="container">
"""

# JavaScript para abrir e fechar a matéria
HTML_JS = """
<script>
function abrirMateria(id) {
    document.getElementById('modal-' + id).style.display = 'block';
    document.body.style.overflow = 'hidden'; // Trava o scroll do fundo
}
function fecharMateria(id) {
    document.getElementById('modal-' + id).style.display = 'none';
    document.body.style.overflow = 'auto';
}
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}
</script>
"""

HTML_TEMPLATE_FIM = f"{HTML_JS}</div><footer style='text-align:center; padding:40px; color:#999;'>Portal IA News</footer></body></html>"

def extrair_imagem(entry):
    if 'media_content' in entry: return entry.media_content[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''): return link.get('href')
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=800&auto=format&fit=crop"

def processar_noticia(titulo, resumo):
    # Pedimos explicitamente um RESUMO curto e uma MATÉRIA detalhada
    prompt = f"Aja como um jornalista. Baseado em Título: {titulo} e Resumo: {resumo}, crie:\nRESUMO: [1 frase chamativa]\nMATERIA: [3 parágrafos detalhados]\nTAGS: [3 tags]"
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except: return None

def formatar_para_html(conteudo_ia, url_img, id_noticia):
    try:
        linhas = conteudo_ia.split('\n')
        resumo = [l for l in linhas if "RESUMO:" in l][0].replace("RESUMO:", "").strip()
        materia = [l for l in linhas if "MATERIA:" in l][0].replace("MATERIA:", "").strip()
        # Se a matéria vier em várias linhas, pegamos o bloco
        if "MATERIA:" in conteudo_ia:
            materia = conteudo_ia.split("MATERIA:")[1].split("TAGS:")[0].strip()
        
        return f"""
        <div class="noticia-card" onclick="abrirMateria('{id_noticia}')">
            <img class="noticia-img" src="{url_img}">
            <div class="noticia-content">
                <h2>{resumo}</h2>
            </div>
        </div>
        
        <div id="modal-{id_noticia}" class="modal">
            <div class="modal-content">
                <span class="close-btn" onclick="fecharMateria('{id_noticia}')">&times;</span>
                <img src="{url_img}" class="modal-img">
                <h1 style="line-height: 1.2;">{resumo}</h1>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <div class="texto-completo">{materia.replace(chr(10), '<br><br>')}</div>
            </div>
        </div>
        """
    except: return ""

def gerar_site():
    print("Gerando portal com sistema de leitura completa...")
    conteudo_dinamico = ""
    contador = 0
    for categoria, url in FEEDS.items():
        conteudo_dinamico += f"<h2 class='categoria-titulo'>{categoria}</h2><div class='grid-noticias'>"
        feed = feedparser.parse(url)
        for entry in feed.entries[:4]: # 4 notícias por categoria
            url_img = extrair_imagem(entry)
            texto_ia = processar_noticia(entry.title, entry.summary)
            if texto_ia:
                conteudo_dinamico += formatar_para_html(texto_ia, url_img, contador)
                contador += 1
            time.sleep(2)
        conteudo_dinamico += "</div>"

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE_INICIO + conteudo_dinamico + HTML_TEMPLATE_FIM)
    print("✅ Portal atualizado!")

if __name__ == "__main__":
    gerar_site()
