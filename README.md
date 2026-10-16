# Orientador UDG CUTonalá (backend)

## Arrancar (3 pasos)
1. Abre esta carpeta en VS Code (Archivo → Abrir carpeta).
2. Terminal → Nueva terminal, y ejecuta (una sola vez):
   - Windows:  `python -m venv .venv` → `.venv\Scripts\activate` → `pip install -r requirements.txt`
   - Mac/Linux: `python3 -m venv .venv` → `source .venv/bin/activate` → `pip install -r requirements.txt`
3. Presiona **F5** (o en la terminal: `uvicorn app.main:app --reload`).

Abre http://127.0.0.1:8000/docs para probar la IA sin frontend.

## Dónde meter tu información
Carpeta `data/`. Cada entrada de `clase_vacia.json` tiene `level` = `personal`, `udg` o `legal`.
Cambia el texto, pon `"verified": true` cuando lo confirmes con tu documento oficial.

## IA generativa (opcional)
Copia `.env.example` a `.env` y pega tu `ANTHROPIC_API_KEY`. Sin key funciona igual (modo gratis).
