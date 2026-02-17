"""
Carrega PDFs e faz chunking para o sistema RAG.

Estratégia:
- Lê todos os PDFs de backend/app/data/pdfs/
- Faz split por parágrafos (double newline)
- Chunks de ~500 chars com overlap de 50 chars
- Retorna lista de dicts com {text, source}
"""

import os
from PyPDF2 import PdfReader


PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def load_pdfs() -> list[dict]:
    """Carrega todos os PDFs do diretório e retorna lista de {text, source}."""
    documents = []

    if not os.path.exists(PDF_DIR):
        print(f"⚠️ Diretório de PDFs não encontrado: {PDF_DIR}")
        return documents

    for filename in sorted(os.listdir(PDF_DIR)):
        if not filename.endswith(".pdf"):
            continue

        filepath = os.path.join(PDF_DIR, filename)
        try:
            reader = PdfReader(filepath)
            full_text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

            if full_text.strip():
                documents.append({
                    "text": full_text.strip(),
                    "source": filename,
                })
                print(f"  📄 Carregado: {filename} ({len(full_text)} chars)")
        except Exception as e:
            print(f"  ❌ Erro ao ler {filename}: {e}")

    print(f"📚 {len(documents)} PDFs carregados")
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Divide documentos em chunks menores com overlap."""
    chunks = []

    for doc in documents:
        text = doc["text"]
        source = doc["source"]

        # Primeiro: split por parágrafos (double newline)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Agrupa parágrafos em chunks de ~CHUNK_SIZE chars
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= CHUNK_SIZE:
                current_chunk += ("\n\n" + para) if current_chunk else para
            else:
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "source": source,
                    })
                # Se o parágrafo é maior que CHUNK_SIZE, divide por caracteres
                if len(para) > CHUNK_SIZE:
                    for i in range(0, len(para), CHUNK_SIZE - CHUNK_OVERLAP):
                        sub = para[i:i + CHUNK_SIZE]
                        if sub.strip():
                            chunks.append({
                                "text": sub.strip(),
                                "source": source,
                            })
                    current_chunk = ""  # reset após sub-chunking
                else:
                    current_chunk = para

        # Último chunk
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "source": source,
            })

    print(f"🔪 {len(chunks)} chunks criados a partir de {len(documents)} documentos")
    return chunks


def load_and_chunk() -> list[dict]:
    """Pipeline completo: carrega PDFs e retorna chunks."""
    documents = load_pdfs()
    return chunk_documents(documents)
