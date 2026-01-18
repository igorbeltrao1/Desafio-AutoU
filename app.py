from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import re

load_dotenv()

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')

ALLOWED_EXTENSIONS = {'txt', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024

def allowedFile(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extrairTextoPdf(fileStream):
    try:
        pdfReader = PdfReader(fileStream)
        textoCompleto = []
        
        for page in pdfReader.pages:
            texto = page.extract_text()
            if texto:
                textoCompleto.append(texto)
        
        return '\n'.join(textoCompleto)
    
    except Exception as e:
        return None

def extrairTextoTxt(fileStream):
    try:
        texto = fileStream.read().decode('utf-8')
        return texto
    except:
        try:
            fileStream.seek(0)
            texto = fileStream.read().decode('latin-1')
            return texto
        except Exception as e:
            return None

def classificarEmailComIa(texto):
    try:
        client = InferenceClient(token=HF_API_KEY)
        
        prompt = f"""Classifique este email em uma das categorias:

PRODUTIVO: Emails que requerem ação ou resposta (solicitações, dúvidas sobre serviços, problemas técnicos, pedidos de status, informações importantes)

IMPRODUTIVO: Emails que não requerem ação imediata (felicitações, agradecimentos sociais, mensagens de cortesia, apresentações pessoais simples)

Email: "{texto[:500]}"

Responda apenas com uma palavra: PRODUTIVO ou IMPRODUTIVO

Categoria:"""
        
        modelos = [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "google/gemma-2-2b-it",
            "Qwen/Qwen2.5-7B-Instruct"
        ]
        
        for modelo in modelos:
            try:
                response = client.chat_completion(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=10,
                    temperature=0.1
                )
                
                resposta = response.choices[0].message.content.upper()
                
                if 'PRODUTIVO' in resposta and 'IMPRODUTIVO' not in resposta:
                    return "Produtivo", "IA Hugging Face"
                elif 'IMPRODUTIVO' in resposta:
                    return "Improdutivo", "IA Hugging Face"
                
            except Exception:
                continue
        
        raise Exception("Nenhum modelo de IA disponível no momento")
    
    except Exception as e:
        raise Exception(f"Erro ao classificar com IA: {str(e)}")

def gerarRespostaComIa(texto, categoria):
    try:
        client = InferenceClient(token=HF_API_KEY)
        
        if categoria == "Produtivo":
            prompt = f"""Você é um assistente profissional de atendimento ao cliente.

Email recebido: {texto}

Escreva UMA resposta profissional e específica:
- Confirme recebimento
- Seja específico sobre o assunto mencionado
- Se há número/protocolo, mencione-o
- Tom profissional mas cordial
- Máximo 4 linhas
- Assine como "Equipe de Atendimento"

Resposta:"""
        else:
            prompt = f"""Você é um assistente amigável.

Mensagem recebida: {texto}

Escreva UMA resposta calorosa e pessoal:
- Agradeça pela mensagem
- Seja genuíno
- Se mencionou nome, use-o
- Máximo 3 linhas
- Assine como "Equipe"

Resposta:"""
        
        modelos = [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "google/gemma-2-2b-it",
            "Qwen/Qwen2.5-7B-Instruct"
        ]
        
        for modelo in modelos:
            try:
                response = client.chat_completion(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7
                )
                
                resposta = response.choices[0].message.content.strip()
                
                if len(resposta) > 30:
                    return resposta
                
            except Exception:
                continue
        
        raise Exception("Nenhum modelo de IA disponível para gerar resposta")
    
    except Exception as e:
        raise Exception(f"Erro ao gerar resposta com IA: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/classificar', methods=['POST'])
def classificar():
    try:
        texto = None
        fonte = "texto"
        
        if 'arquivo' in request.files:
            file = request.files['arquivo']
            
            if file.filename == '':
                return jsonify({'erro': 'Nenhum arquivo selecionado'}), 400
            
            if not allowedFile(file.filename):
                return jsonify({'erro': 'Formato não permitido. Use .txt ou .pdf'}), 400
            
            filename = secure_filename(file.filename)
            fileExt = filename.rsplit('.', 1)[1].lower()
            
            if fileExt == 'pdf':
                texto = extrairTextoPdf(file)
                fonte = "PDF"
            elif fileExt == 'txt':
                texto = extrairTextoTxt(file)
                fonte = "TXT"
            
            if not texto:
                return jsonify({'erro': 'Não foi possível extrair texto do arquivo'}), 400
        
        else:
            texto = request.form.get('texto', '').strip()
            fonte = "texto"
        
        if not texto:
            return jsonify({'erro': 'Por favor, insira o texto ou faça upload de um arquivo'}), 400
        
        if len(texto) < 10:
            return jsonify({'erro': 'Texto muito curto. Insira pelo menos 10 caracteres.'}), 400
        
        try:
            categoria, metodo = classificarEmailComIa(texto)
        except Exception as e:
            return jsonify({'erro': f'Serviço de IA temporariamente indisponível: {str(e)}'}), 503
        
        try:
            resposta = gerarRespostaComIa(texto, categoria)
        except Exception as e:
            return jsonify({'erro': f'Erro ao gerar resposta com IA: {str(e)}'}), 503
        
        resultado = {
            'categoria': categoria,
            'resposta': resposta,
            'caracteres': len(texto),
            'palavras': len(texto.split()),
            'fonte': fonte,
            'metodo': metodo
        }
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao processar solicitação: {str(e)}'}), 500

if __name__ == '__main__':
    if not HF_API_KEY:
        print("ERRO: HUGGINGFACE_API_KEY não encontrada")
        exit(1)
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)
     