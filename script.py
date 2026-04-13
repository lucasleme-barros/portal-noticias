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
# 2. TEMPLATE HTML (MODO CLEAN)
# ==========================================
HTML_TEMPLATE_INICIO = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA News Portal</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; color: #1c1e21; margin: 0; padding: 0; }}
        header {{ background: #ffffff; padding: 30px 20px; text-align: center; border-bottom: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }}
        header h1 {{ margin: 0; font-size: 2em; color: #1a73e8; text-transform: uppercase; letter-spacing: 1px; }}
        
        .container {{ max-width: 1200px; margin: 40px auto; padding: 0 20px; }}
        .categoria-titulo {{ color: #d93025; border-bottom: 2px solid #d93025; display: inline-block; padding-bottom: 5px; margin-top: 40px; text-transform: uppercase; font-size: 1.1em; font-weight: bold; }}
        
        .grid-noticias {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; margin-top: 20px; }}
        
        .noticia-card {{ background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.2); cursor: pointer; transition: 0.3s; display: flex; flex-direction: column; }}
        .noticia-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 16px rgba(0,0,0,0.2); }}
        
        .noticia-img {{ width: 100%; height: 180px; object-fit: cover; background: #eee; }}
        .noticia-content {{ padding: 15px; flex-grow: 1; }}
        .noticia-card h2 {{ margin: 0; font-size: 1.1em; color: #000; line-height: 1.4; }}
        
        /* MODAL */
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); overflow-y: auto; backdrop-filter: blur(4px); }}
        .modal-content {{ background: #fff; margin: 2% auto; padding: 40px; width: 90%; max-width: 700px; border-radius: 12px; position: relative; line-height: 1.8; color: #444; }}
        .close-btn {{ position: absolute; right: 25px; top: 15px; font-size: 35px; cursor: pointer; color: #aaa; }}
        .modal-img {{ width: 100%; max-height: 350px; object-fit: cover; border-radius: 8px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <header>
        <h1>Portal Notícias IA</h1>
        <p style="color: #666; font-size: 0.85em; margin-top:10px;">Última atualização: {agora}</p>
    </header>
    <div class="container">
"""

HTML_JS = """
<script>
function abrirMateria(id) {
    document.getElementById('modal-' + id).style.display = 'block';
    document.body.style.overflow = 'hidden';
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

HTML_TEMPLATE_FIM = f"{HTML_JS}</div><footer style='text-align:center; padding:60px; color:#888; font-size: 0.8em;'>© 2026 Portal de Notícias Inteligente</footer></body></html>"

# ==========================================
# 3. FUNÇÕES
# ==========================================
def extrair_imagem(entry):
    if 'media_content' in entry: return entry.media_content[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''): return link.get('href')
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80"

def processar_noticia(titulo, resumo):
    prompt = f"Baseado em Título: {titulo} e Resumo: {resumo}, escreva uma notícia curta em português. Use este formato exato:\n[RESUMO]\n(Sua manchete aqui)\n[MATERIA]\n(Seu texto aqui em 2 parágrafos)\n[FIM]"
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return response.text
    except: return None

def formatar_para_html(texto_ia, url_img, id_noticia):
    try:
        # Lógica de extração mais robusta baseada nos colchetes
        resumo = texto_ia.split("[RESUMO]")[1].split("[MATERIA]")[0].strip()
        materia = texto_ia.split("[MATERIA]")[1].split("[FIM]")[0].strip()
        
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
                <h1 style="color:#111; line-height: 1.2; margin-bottom:20px;">{resumo}</h1>
                <div style="font-size: 1.1em;">{materia.replace(chr(10), '<br><br>')}</div>
            </div>
        </div>
        """
    except Exception as e:
        print(f"Erro ao formatar card {id_noticia}: {e}")
        return ""

def gerar_site():
    print("Iniciando reconstrução do portal...")
    conteudo_dinamico = ""
    contador = 0
    
    for categoria, url in FEEDS.items():
        print(f"Processando categoria: {categoria}")
        secao_html = f"<h2 class='categoria-titulo'>{categoria}</h2><div class='grid-noticias'>"
        feed = feedparser.parse(url)
        
        itens_adicionados = 0
        for entry in feed.entries[:5]:
            if itens_adicionados >= 3: break # Limite de 3 notícias por categoria
            
            url_img = extrair_imagem(entry)
            texto_ia = processar_noticia(entry.title, entry.summary)
            
            if texto_ia and "[RESUMO]" in texto_ia:
                card = formatar_para_html(texto_ia, url_img, contador)
                if card:
                    secao_html += card
                    contador += 1
                    itens_adicionados += 1
            time.sleep(2)
            
        secao_html += "</div>"
        conteudo_dinamico += secao_html

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE_INICIO + conteudo_dinamico + HTML_TEMPLATE_FIM)
    print(f"✅ Sucesso! {contador} notícias geradas.")

if __name__ == "__main__":
    gerar_site()
