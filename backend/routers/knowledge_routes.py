import io
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from database import db, clean_list
from auth import get_current_user
from rag import chunk_text
from workflow import now_iso

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class TextDoc(BaseModel):
    source: str
    content: str


def _extract(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    raise HTTPException(400, "Format tidak didukung. Gunakan .txt, .md, .pdf, atau .docx")


async def _store(source: str, text: str):
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(400, "Dokumen kosong atau tidak dapat dibaca")
    doc_id = str(uuid.uuid4())
    await db.knowledge_docs.insert_one({
        "id": doc_id, "source": source, "chunk_count": len(chunks),
        "chars": len(text), "created_at": now_iso()})
    await db.knowledge_chunks.insert_many([
        {"id": str(uuid.uuid4()), "doc_id": doc_id, "source": source, "text": c}
        for c in chunks])
    return {"id": doc_id, "source": source, "chunk_count": len(chunks)}


@router.get("")
async def list_docs(user=Depends(get_current_user)):
    docs = await db.knowledge_docs.find().sort("created_at", -1).to_list(500)
    return clean_list(docs)


@router.post("/upload")
async def upload(file: UploadFile = File(...), user=Depends(get_current_user)):
    data = await file.read()
    text = _extract(file.filename, data)
    return await _store(file.filename, text)


@router.post("/text")
async def add_text(doc: TextDoc, user=Depends(get_current_user)):
    return await _store(doc.source, doc.content)


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str, user=Depends(get_current_user)):
    await db.knowledge_docs.delete_one({"id": doc_id})
    await db.knowledge_chunks.delete_many({"doc_id": doc_id})
    return {"ok": True}
