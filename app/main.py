"""Backend del Orientador UDG CUTonalá (FastAPI).

Arrancar:  uvicorn app.main:app --reload
Docs automáticas: http://127.0.0.1:8000/docs
"""
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .knowledge import LEVEL_LABELS, LEVEL_ORDER, KnowledgeBase
from .bot import Flow

kb = KnowledgeBase()
flow = Flow(kb)
app = FastAPI(title="Orientador UDG CUTonalá", version="1.0.0")

# CORS abierto para desarrollo: el frontend puede vivir en otro puerto.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ---------- Modelos (el contrato con el frontend) ----------
class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: list[Turn] = Field(default_factory=list, description="Mensajes previos (opcional)")
    state: str | None = Field(None, description="Estado actual del autómata (el que devolvió la respuesta anterior)")


class Section(BaseModel):
    level: Literal["personal", "udg", "legal"]
    level_label: str
    id: str
    title: str
    content: str
    steps: list[str]
    verified: bool
    source: str


class ChatResponse(BaseModel):
    answer: str
    sections: list[Section]
    in_scope: bool
    mode: Literal["flow", "retrieval"]
    state: str
    options: list[str]
    suggested_questions: list[str]
    disclaimer: str


# ---------- Endpoints ----------
@app.get("/api/health")
def health():
    return {"status": "ok", "entries": len(kb.entries), "states": len(flow.estados)}


@app.get("/api/config")
def config():
    c = kb.config
    return {
        "institution": c["institution"],
        "assistant_name": c["assistant_name"],
        "current_topic": c["current_topic"],
        "welcome": c["welcome"],
        "suggested_questions": c["suggested_questions"],
        "disclaimer": c["disclaimer"],
        "levels": [{"id": l, "label": LEVEL_LABELS[l]} for l in LEVEL_ORDER],
        "start": {k: v for k, v in flow.render(flow.inicial).items() if k in ("answer", "state", "options")},
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    c = kb.config
    r = flow.step(req.message, req.state or flow.inicial)
    sections = [
        Section(
            level=e["level"],
            level_label=LEVEL_LABELS[e["level"]],
            id=e["id"],
            title=e["title"],
            content=e["content"],
            steps=e.get("steps", []),
            verified=e.get("verified", False),
            source=e.get("source", ""),
        )
        for e in r["sections"]
    ]
    return ChatResponse(
        answer=r["answer"],
        sections=sections,
        in_scope=r["in_scope"],
        mode=r["mode"],
        state=r["state"],
        options=r["options"],
        suggested_questions=c["suggested_questions"],
        disclaimer=c["disclaimer"],
    )


# ---------- Frontend (si existe la carpeta /frontend se sirve en "/") ----------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if (FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")