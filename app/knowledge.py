"""Base de conocimiento + buscador (sin librerías externas).

Lee los .json de la carpeta data/ y, dada una pregunta, devuelve las
entradas más parecidas agrupadas por nivel: personal, udg, legal.
"""
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

LEVEL_LABELS = {
    "personal": "Nivel personal: lo que puedes hacer tú",
    "udg": "Nivel UDG: instancias universitarias",
    "legal": "Nivel legal: derechos y normativa",
}
LEVEL_ORDER = ["personal", "udg", "legal"]

STOPWORDS = set(
    "a al algo ante con como cual cuando de del el ella en es esta este "
    "la las lo los me mi mis muy no o para pero por que se si sin su sus "
    "te tu un una uno y ya hay he ha fue son ser soy mas".split()
)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", text)


def tokenize(text: str) -> list[str]:
    out = []
    for w in normalize(text).split():
        if w in STOPWORDS or len(w) < 2:
            continue
        out.append(w[:5] if len(w) > 5 else w)  # "stem" simple: maestro/maestros
    return out


class KnowledgeBase:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.config = json.loads((data_dir / "config.json").read_text(encoding="utf-8"))
        self.entries: list[dict] = []
        for f in sorted(data_dir.glob("*.json")):
            if f.name == "config.json":
                continue
            self.entries.extend(json.loads(f.read_text(encoding="utf-8")))
        self._index()

    def _index(self):
        self.docs = []
        df = Counter()
        for e in self.entries:
            weighted = (
                (e["title"] + " ") * 3
                + (" ".join(e.get("keywords", [])) + " ") * 3
                + e["content"]
                + " "
                + " ".join(e.get("steps", []))
            )
            tf = Counter(tokenize(weighted))
            self.docs.append(tf)
            df.update(tf.keys())
        n = max(len(self.docs), 1)
        self.idf = {t: math.log(1 + n / c) for t, c in df.items()}

    def score(self, query: str, i: int) -> float:
        tf = self.docs[i]
        total = sum(tf.values()) or 1
        s = 0.0
        for t in set(tokenize(query)):
            if t in tf:
                s += self.idf.get(t, 0) * (1 + math.log(1 + tf[t])) / (1 + math.log(total))
        return s

    def _oos_hit(self, query: str):
        """Entrada 'fuera de alcance' (acoso, etc.) si la pregunta trae una de sus palabras clave."""
        q = " " + normalize(query) + " "
        for e in self.entries:
            if e.get("in_scope") is False:
                for k in e.get("keywords", []):
                    if " " + normalize(k).strip() + " " in q:
                        return e
        return None

    def search(self, query: str, per_level: int = 2, min_score: float = 0.25):
        """Devuelve ({'personal': [...], 'udg': [...], 'legal': [...]}, entrada_fuera_de_alcance)."""
        result = {lvl: [] for lvl in LEVEL_ORDER}
        out_of_scope = self._oos_hit(query)
        if out_of_scope:
            return result, out_of_scope
        scored = sorted(
            ((self.score(query, i), e) for i, e in enumerate(self.entries)),
            key=lambda x: x[0],
            reverse=True,
        )
        for s, e in scored:
            if s < min_score:
                break
            if e.get("in_scope") is False:
                continue
            if len(result[e["level"]]) < per_level:
                result[e["level"]].append({**e, "score": round(s, 3)})
        return result, None
