"""Local-only RAG with Chroma and the Ollama embeddings API."""
import requests
from .config import CHROMA_DIR, EMBED_MODEL, OLLAMA_URL

COLLECTION = 'interview_knowledge'

def embed(texts: list[str]) -> list[list[float]]:
    response = requests.post(
        f'{OLLAMA_URL}/api/embed',
        json={'model': EMBED_MODEL, 'input': texts}, timeout=120,
    )
    response.raise_for_status()
    return response.json()['embeddings']

def get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION)

def search(query: str, limit: int = 3) -> str:
    """Empty string is okay before students index their knowledge files."""
    collection = get_collection()
    if collection.count() == 0:
        return ''
    result = collection.query(
        query_embeddings=embed([query]),
        n_results=min(limit, collection.count()),
        include=['documents', 'metadatas'],
    )
    excerpts = []
    for content, metadata in zip(result['documents'][0], result['metadatas'][0]):
        excerpts.append(f"Source: {metadata.get('source', 'notes')}\n{content}")
    return '\n\n'.join(excerpts)
