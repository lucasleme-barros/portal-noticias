import os
from google import genai
import feedparser
import time
from datetime import datetime
import pytz

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)

# Configuração de fuso horário para o carimbo de atualização
fuso = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso).strftime('%d/%m/%Y %H:%M:%S')

# Fontes de Notícias
FEEDS = {
    "Mundo & Atualidades": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Games & Tecnologia": "https://br.ign.com/feed.xml"
}

# ==========================================
# 2. ESTRUTURA VISUAL (HTML/CSS)
# ==========================================
HTML_TEMPLATE_INICIO = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA News Portal</title>
    <style>
        body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f8f9fa; color: #202124; margin: 0; padding: 0; }}
        header {{ background: #ffffff; padding: 25px 20px; text-align: center; border-bottom: 1px solid #e0e0e0; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
        header h1 {{ margin: 0; font-size: 2.2em; color: #d93025; text-transform: uppercase; letter-spacing: 1px; }}
        header p {{ color: #5f6368; font-size: 0.85em; margin-top: 8px; }}
        
        .container {{ max-width: 1200px; margin: 20px auto; padding: 20px; }}
        .categoria-titulo {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; display: inline-block; padding-bottom: 5px; margin-top: 30px; margin-bottom: 20px; text-transform: uppercase; font-size: 1em; font-weight: bold; }}
        
        .grid-noticias {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; }}
        
        .noticia-card {{ background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.12); cursor: pointer; transition: all 0.3s ease; display: flex; flex-direction: column; border: 1px solid #e0e0e0; }}
        .noticia-card:hover {{ transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); border-color: #1a73e8; }}
        
        .noticia-img {{ width: 100%; height: 180px; object-fit: cover; background: #f1f3f4; }}
        .noticia-content {{ padding: 15px; flex-grow: 1; }}
        .noticia-card h2 {{ margin: 0; font-size: 1.05em; color: #111; line-height: 1.4; font-weight: 600; }}
        
        /* MODAL DE LEITURA COMPLETA */
        .modal {{ display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); overflow-y: auto; backdrop-filter: blur(3px); }}
        .modal-content {{ background: #fff; margin: 3% auto; padding: 35px; width: 90%; max-width: 750px; border-radius: 12px; position: relative; line-height: 1.8; color: #3c4043; }}
        .close-btn {{ position: absolute; right: 20px; top: 10px; font-size: 35px; cursor: pointer; color: #70757a; }}
        .modal-img {{ width: 100%; max-height: 380px; object-fit: cover; border-radius: 8px; margin-bottom: 25px; }}
        .modal-body {{ font-size: 1.15em; }}
    </style>
</head>
<body>
    <header>
        <h1>Portal Notícias IA</h1>
        <p>Última atualização: {agora}</p>
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
// Fecha ao clicar fora da janela
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}
</script>
"""

HTML_TEMPLATE_FIM = f"""
    {HTML_JS}
    </div>
    <footer style="text-align:center; padding:60px 20px; color:#70757a; font-size: 0.85em; border-top: 1px solid #e0e0e0; margin-top: 50px;">
        <p>Gerado por Inteligência Artificial • GitHub Actions • Gemini 2.0 Flash</p>
    </footer>
</body>
</html>
"""

# ==========================================
# 3. LÓGICA DO SISTEMA (PYTHON)
# ==========================================

def extrair_imagem(entry):
    """Tenta capturar a imagem do feed RSS."""
    if 'media_content' in entry: return entry.media_content[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''): return link.get('href')
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80"

def processar_noticia(titulo, resumo):
    """Envia para a IA gerar o conteúdo formatado."""
    prompt = (
        f"Aja como um redator de notícias. Baseado no Título: {titulo} e Resumo: {resumo}, "
        "gere uma versão curta e envolvente. Responda rigorosamente neste formato:\n"
        "[RESUMO]\n(Sua manchete aqui)\n"
        "[MATERIA]\n(Seu texto detalhado aqui em 2 ou 3 parágrafos)\n"
        "[FIM]"
    )
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return response.text
    except Exception as e:
        print(f"Erro na API Gemini: {e}")
        return None

def formatar_para_html(texto_ia, url_img, id_noticia):
    """Quebra o texto da IA e monta o HTML do card e do modal."""
    try:
        if "[RESUMO]" in texto_ia and "[MATERIA]" in texto_ia:
            resumo = texto_ia.split("[RESUMO]")[1].split("[MATERIA]")[0].strip()
            # Pega o conteúdo da matéria até o [FIM] ou até o final do texto
            resto = texto_ia.split("[MATERIA]")[1]
            materia = resto.split("[FIM]")[0].strip() if "[FIM]" in resto else resto.strip()
            
            return f"""
            <div class="noticia-card" onclick="abrirMateria('{id_noticia}')">
                <img class="noticia-img" src="{url_img}" alt="Notícia">
                <div class="noticia-content">
                    <h2>{resumo}</h2>
                </div>
            </div>
            
            <div id="modal-{id_noticia}" class="modal">
                <div class="modal-content">
                    <span class="close-btn" onclick="fecharMateria('{id_noticia}')">&times;</span>
                    <img src="{url_img}" class="modal-img">
                    <h1 style="color:#111; line-height: 1.2; margin-bottom:20px; font-size: 1.8em;">{resumo}</h1>
                    <div class="modal-body">{materia.replace(chr(10), '<br><br>')}</div>
                </div>
            </div>
            """
    except Exception as e:
        print(f"Erro ao formatar notícia {id_noticia}: {e}")
    return ""

def gerar_site():
    """Função principal que coordena o fluxo."""
    print(f"Iniciando reconstrução do portal às {agora}...")
    conteudo_dinamico = ""
    contador_global = 0
    
    for categoria, url in FEEDS.items():
        print(f"Processando categoria: {categoria}")
        secao_html = f"<h2 class='categoria-titulo'>{categoria}</h2><div class='grid-noticias'>"
        feed = feedparser.parse(url)
        
        sucessos = 0
        # Tenta as 10 notícias mais recentes do feed para garantir que achamos 3 válidas
        for entry in feed.entries[:10]:
            if sucessos >= 3: break
            
            print(f"  - Analisando: {entry.title[:40]}...")
            url_img = extrair_imagem(entry)
            texto_gerado = processar_noticia(entry.title, entry.summary)
            
            if texto_gerado and "[RESUMO]" in texto_gerado:
                html_noticia = formatar_para_html(texto_gerado, url_img, contador_global)
                if html_noticia:
                    secao_html += html_noticia
                    contador_global += 1
                    sucessos += 1
            
            time.sleep(2) # Evita sobrecarga na API
            
        secao_html += "</div>"
        conteudo_dinamico += secao_html

    # Salva o arquivo final
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE_INICIO + conteudo_dinamico + HTML_TEMPLATE_FIM)
    
    print(f"✅ Portal finalizado com sucesso! Total de {contador_global} notícias.")

if __name__ == "__main__":
    gerar_site()
