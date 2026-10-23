"""Run from project root: python -m backend.ingest"""
from pathlib import Path
from pypdf import PdfReader
from .app.config import ROOT
from .app.rag import embed, get_collection

SOURCE_DIR = ROOT / 'knowledge'

def extract(path: Path) -> str:
    if path.suffix.lower() == '.pdf':
        return '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
    return path.read_text(encoding='utf-8')

def chunks(text: str, size: int = 700, overlap: int = 100):
    text = ' '.join(text.split())
    for start in range(0, len(text), size - overlap):
        chunk = text[start:start + size]
        if len(chunk) >= 50:
            yield chunk
        if start + size >= len(text):
            break

def main():
    ids, documents, metadata = [], [], []
    for path in sorted(SOURCE_DIR.iterdir()):
        if path.suffix.lower() not in {'.txt', '.pdf'}:
            continue
        for index, chunk in enumerate(chunks(extract(path))):
            ids.append(f'{path.stem}-{index}')
            documents.append(chunk)
            metadata.append({'source': path.name, 'chunk': index})
    if not documents:
        print('No notes found in knowledge/.')
        return
    collection = get_collection()
    for i in range(0, len(documents), 16):
        batch = slice(i, i + 16)
        collection.upsert(ids=ids[batch], documents=documents[batch],
                          metadatas=metadata[batch],
                          embeddings=embed(documents[batch]))
    print(f'Indexed {len(documents)} chunks in local Chroma.')

if __name__ == '__main__':
    main()
