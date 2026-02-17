import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ Erro: GOOGLE_API_KEY não encontrada no .env")
    exit(1)

print(f"🔑 Usando API Key: {api_key[:5]}...{api_key[-5:]}")

try:
    genai.configure(api_key=api_key)
    
    print("\n🔍 Buscando modelos disponíveis...")
    found = False
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ {m.name}")
            found = True
            
    if not found:
        print("⚠️ Nenhum modelo com suporte a 'generateContent' encontrado.")
        
except Exception as e:
    print(f"\n❌ Erro ao listar modelos: {str(e)}")
