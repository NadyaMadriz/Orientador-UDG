"""Autómata de estados finitos del Orientador UDG.

Cada ESTADO tiene un texto, fichas que muestra y OPCIONES; cada opción es una
TRANSICIÓN hacia otro estado. El flujo vive en app/flujo.json (editable).

Además del flujo guiado hay INTENCIONES globales (sección "intenciones" del
JSON): frases cotidianas que llevan a un estado desde cualquier punto, para
que el estudiante pueda preguntar con sus palabras sin seguir el menú.

Orden de decisión en cada mensaje:
  0) reiniciar
  1) tema fuera de alcance (acoso, etc.) -> aviso delicado
  2) opción del estado actual vs. intención global -> gana la coincidencia
     más específica (la palabra clave más larga; en empate, la opción)
  3) pregunta libre: ficha más parecida (búsqueda), sin cambiar de estado
  4) no se entendió: repetir la pregunta del estado
"""
import json
from pathlib import Path

from .knowledge import LEVEL_ORDER, normalize

FLUJO_PATH = Path(__file__).resolve().parent / "flujo.json"
UMBRAL_FICHA = 0.5  # qué tan parecida debe ser una ficha para responder con ella


class Flow:
    def __init__(self, kb):
        data = json.loads(FLUJO_PATH.read_text(encoding="utf-8"))
        self.estados = data["estados"]
        self.inicial = data["inicio_estado"]
        self.intenciones = data.get("intenciones", [])
        self.kb = kb
        self.fichas = {e["id"]: e for e in kb.entries}
        self._validar()

    def _validar(self):
        """Falla al arrancar (no en producción) si el JSON apunta a un estado inexistente."""
        for nombre, s in self.estados.items():
            for op in s.get("opciones", []):
                if op["siguiente"] not in self.estados:
                    raise ValueError(f"Estado '{nombre}': la opción '{op['texto']}' apunta a '{op['siguiente']}', que no existe")
        for it in self.intenciones:
            if it["estado"] not in self.estados:
                raise ValueError(f"Intención hacia '{it['estado']}': ese estado no existe")

    # ---- mostrar un estado ----
    def render(self, estado_id, prefijo=""):
        s = self.estados[estado_id]
        partes = [p for p in (prefijo, s["texto"], s.get("pregunta", "")) if p]
        return {
            "answer": "\n\n".join(partes),
            "sections": [self.fichas[i] for i in s.get("fichas", []) if i in self.fichas],
            "state": estado_id,
            "options": [o["texto"] for o in s.get("opciones", [])],
            "in_scope": True,
            "mode": "flow",
        }

    # ---- coincidencias ----
    @staticmethod
    def _mejor_clave(texto_norm, claves):
        """Longitud de la clave más larga que aparece como palabra(s) completa(s); 0 si ninguna."""
        mejor = 0
        for k in claves:
            k = normalize(k).strip()
            if k and f" {k} " in texto_norm and len(k) > mejor:
                mejor = len(k)
        return mejor

    def _coincide(self, estado_id, mensaje):
        """Opción del estado actual que mejor coincide -> (opción, largo) o (None, 0)."""
        t = " " + normalize(mensaje) + " "
        mejor, largo = None, 0
        for op in self.estados[estado_id].get("opciones", []):
            n = self._mejor_clave(t, [op["texto"]] + op.get("palabras", []))
            if n > largo:
                mejor, largo = op, n
        return mejor, largo

    def _intencion(self, mensaje):
        """Intención global que mejor coincide -> (estado, largo) o (None, 0)."""
        t = " " + normalize(mensaje) + " "
        mejor, largo = None, 0
        for it in self.intenciones:
            n = self._mejor_clave(t, it["palabras"])
            if n > largo:
                mejor, largo = it["estado"], n
        return mejor, largo

    def step(self, mensaje, estado_id):
        if estado_id not in self.estados:
            estado_id = self.inicial

        # 0) Reiniciar en cualquier momento
        n = normalize(mensaje)
        if "reiniciar" in n or "empezar de nuevo" in n:
            return self.render(self.inicial)

        # 1) Temas fuera de alcance (acoso, etc.): siempre tienen prioridad
        resultados, oos = self.kb.search(mensaje)
        if oos:
            r = self.render(estado_id)
            r.update(answer=oos["content"], sections=[], in_scope=False, options=["Empezar de nuevo"])
            return r

        # 2) Opción del estado actual vs. intención global: gana la más específica
        op, largo_op = self._coincide(estado_id, mensaje)
        destino, largo_int = self._intencion(mensaje)
        if op and largo_op >= largo_int:
            return self.render(op["siguiente"])
        if destino:
            return self.render(destino)

        # 3) Pregunta libre: responder con la ficha más parecida y NO cambiar de estado
        candidatas = [e for lvl in LEVEL_ORDER for e in resultados[lvl]]
        if candidatas:
            mejor = max(candidatas, key=lambda e: e["score"])
            if mejor["score"] >= UMBRAL_FICHA:
                s = self.estados[estado_id]
                r = self.render(estado_id)
                r["sections"] = [mejor]
                r["answer"] = (
                    "Sobre eso, esto es lo que encontré. Seguimos con lo que veníamos:\n\n"
                    + "\n\n".join(p for p in (s["texto"], s.get("pregunta", "")) if p)
                )
                r["mode"] = "retrieval"
                return r

        # 4) No se entendió: repetir la pregunta del estado y ofrecer el menú de temas
        r = self.render(estado_id, prefijo="No te entendí del todo. Elige una opción de abajo, cuéntame con otras palabras o escribe «menú» para ver todos los temas.")
        return r