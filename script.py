import os
from google import genai
import feedparser
import time

# ==========================================
# 1. CONFIGURAÇÕES E CHAVE
# ==========================================
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GOOGLE_API_KEY)

# Dicionário com as categorias e seus respectivos Feeds RSS
FEEDS = {
    "Mundo & Atualidades": "http://feeds.bbci.co.uk/portuguese/rss.xml",
    "Esportes": "https://ge.globo.com/rss/ge/",
    "Games & Tecnologia": "https://br.ign.com/feed.xml"
}

# ==========================================
# 2. TEMPLATES HTML
# ==========================================
HTML_TEMPLATE_INICIO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA News Portal</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #0f111a; color: #e0e0e0; margin: 0; padding: 0; }
        header { background: linear-gradient(90deg, #1a1c2c, #4a192c); padding: 40px 20px; text-align: center; border-bottom: 3px solid #ff4b2b; }
        header h1 { margin: 0; font-size: 2.5em; letter-spacing: 2px; text-transform: uppercase; }
        .container { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
        
        /* Estilos das Categorias */
        .categoria-titulo { color: #ff4b2b; border-bottom: 2px solid #30334a; padding-bottom: 10px; margin-top: 40px; margin-bottom: 20px; font-size: 1.8em; text-transform: uppercase;}
        
        /* Estilos dos Cards */
        .grid-noticias { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .noticia-card { background: #1e2030; padding: 25px; border-radius: 12px; border-top: 4px solid #ff4b2b; box-shadow: 0 8px 15px rgba(0,0,0,0.4); display: flex; flex-direction: column; justify-content: space-between;}
        .noticia-card h2 { margin-top: 0; color: #fff; line-height: 1.3; font-size: 1.3em; }
        .noticia-card p { line-height: 1.6; color: #b0b3b8; font-size: 1em; flex-grow: 1;}
        .tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 15px; }
        .tag { background: #30334a; padding: 4px 10px; border-radius: 15px; font-size: 0.75em; color: #03dac6; font-weight: bold; }
        
        footer { text-align: center; padding: 20px; font-size: 0.9em; color: #666; margin-top: 50px; background: #0a0b10;}
    </style>
</head>
<body>
    <header>
        <h1>Portal IA News</h1>
        <p>Notícias processadas de forma 100% autônoma pelo Gemini</p>
    </header>
    <div class="container">
"""

HTML_TEMPLATE_FIM = """
    </div>
    <footer>Gerado automaticamente via GitHub Actions • Atualizado de hora em hora</footer>
</body>
</html>
"""

# ==========================================
# 3. FUNÇÕES DE PROCESSAMENTO
# ==========================================
def processar_noticia(titulo, resumo):
    prompt = f"Reescreva de forma envolvente para um site. Título: {titulo}. Resumo: {resumo}. Retorne EXATAMENTE no formato:\nTITULO: [titulo]\nCORPO: [paragrafo]\nTAGS: [tag1, tag2, tag3]"
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        print(f"Erro na IA: {e}")
        return None

def formatar_para_html(conteudo_ia):
    try:
        linhas = conteudo_ia.split('\n')
        titulo = [l for l in linhas if "TITULO:" in l][0].replace("TITULO:", "").strip()
        corpo = [l for l in linhas if "CORPO:" in l][0].replace("CORPO:", "").strip()
        tags_raw = [l for l in linhas if "TAGS:" in l][0].replace("TAGS:", "").strip().split(',')
        
        tags_html = "".join([f'<span class="tag">{t.strip()}</span>' for t in tags_raw])
        
        return f"""
        <div class="noticia-card">
            <h2>{titulo}</h2>
            <p>{corpo}</p>
            <div class="tags">{tags_html}</div>
        </div>
        """
    except Exception as e:
        print(f"Erro na formatação: {e}")
        return ""

def gerar_site():
    print("Iniciando geração do site categorizado...")
    conteudo_dinamico = ""
    
    # Itera sobre cada categoria e seu link RSS
    for categoria, url in FEEDS.items():
        print(f"\n>> Buscando notícias para: {categoria}")
        conteudo_dinamico += f"<h2 class='categoria-titulo'>{categoria}</h2>\n<div class='grid-noticias'>"
        
        feed = feedparser.parse(url)
        
        # Pega as 3 primeiras notícias de cada categoria
        for entry in feed.entries[:3]:
            print(f"Processando: {entry.title[:40]}...")
            texto_ia = processar_noticia(entry.title, entry.summary)
            if texto_ia:
                conteudo_dinamico += formatar_para_html(texto_ia)
            time.sleep(3) # Pausa obrigatória para não sobrecarregar a API do Google
            
        conteudo_dinamico += "</div>\n" # Fecha o grid da categoria

    # Monta o arquivo final unindo tudo
    conteudo_completo = HTML_TEMPLATE_INICIO + conteudo_dinamico + HTML_TEMPLATE_FIM
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(conteudo_completo)
    
    print("\n✅ SUCESSO! Site atualizado com categorias.")

if __name__ == "__main__":
    gerar_site()
