import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import db


def chunk_text(text: str, max_words: int = 180):
    """Split raw document text into overlapping-ish chunks of ~180 words."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    words = text.split(" ")
    chunks = []
    for i in range(0, len(words), max_words):
        piece = " ".join(words[i:i + max_words]).strip()
        if piece:
            chunks.append(piece)
    return chunks


async def retrieve(query: str, k: int = 4):
    """TF-IDF cosine similarity retrieval over stored knowledge chunks."""
    docs = await db.knowledge_chunks.find().to_list(3000)
    if not docs:
        return [], 0.0
    texts = [d["text"] for d in docs]
    try:
        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit(texts + [query])
        mat = vec.transform(texts)
        qv = vec.transform([query])
        sims = cosine_similarity(qv, mat)[0]
    except Exception:
        return [], 0.0
    order = sims.argsort()[::-1][:k]
    results = []
    for i in order:
        if sims[i] > 0.02:
            results.append({
                "text": texts[i],
                "score": float(sims[i]),
                "source": docs[i].get("source", "Knowledge Base"),
            })
    top = results[0]["score"] if results else 0.0
    return results, top
