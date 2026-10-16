# Reporte del backend para el frontend — Orientador UDG CUTonalá

> Para la IA que hará el frontend. Este documento es el contrato de la API: adáptate a él, no cambies el backend.

## 1. Resumen
- Backend en **Python + FastAPI**, corre en `http://127.0.0.1:8000`.
- Es un chatbot que orienta a estudiantes de UDG CUTonalá sobre **clases vacías** (maestro que no llega).
- Cada respuesta se organiza en **3 niveles**: `personal`, `udg`, `legal`.
- **CORS abierto** (`*`): el frontend puede estar en otro puerto o abrirse como archivo.
- Si existe `frontend/index.html`, el backend lo sirve solo en `http://127.0.0.1:8000/`. Entrega el frontend como archivos estáticos (HTML/CSS/JS, sin build) dentro de `frontend/` y las llamadas se hacen con rutas relativas (`/api/...`).
- Documentación interactiva autogenerada: `http://127.0.0.1:8000/docs`.

## 2. Endpoints

### GET `/api/config` — llamar al cargar la página
```json
{
  "institution": "Universidad de Guadalajara - CUTonalá",
  "assistant_name": "Orientador UDG",
  "current_topic": "clase_vacia",
  "welcome": "Hola, soy el orientador ... Cuéntame qué pasó.",
  "suggested_questions": ["Mi maestro no llegó a clase, ¿qué hago?", "..."],
  "disclaimer": "Esta orientación es informativa ...",
  "levels": [
    {"id": "personal", "label": "Nivel personal: lo que puedes hacer tú"},
    {"id": "udg",      "label": "Nivel UDG: instancias universitarias"},
    {"id": "legal",    "label": "Nivel legal: derechos y normativa"}
  ]
}
```
Usa `welcome` como primer mensaje del bot y `suggested_questions` como botones/chips.

### POST `/api/chat` — enviar una pregunta
**Request**
```json
{
  "message": "Mi maestro no llegó a clase, ¿qué hago?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```
- `message`: obligatorio, 1–1000 caracteres.
- `history`: opcional. Manda los últimos turnos (`role` = `"user"` | `"assistant"`, `content` = solo el campo `answer` de las respuestas previas). El backend usa los últimos 6.

**Response 200**
```json
{
  "answer": "Texto principal del bot (puede ser corto).",
  "sections": [
    {
      "level": "personal",
      "level_label": "Nivel personal: lo que puedes hacer tú",
      "id": "p-01-esperar",
      "title": "Qué hacer cuando el maestro no llega",
      "content": "Párrafo explicativo...",
      "steps": ["Paso 1", "Paso 2"],
      "verified": false,
      "source": "BORRADOR - reemplazar con tu documento oficial"
    }
  ],
  "in_scope": true,
  "mode": "retrieval",
  "suggested_questions": ["..."],
  "disclaimer": "Esta orientación es informativa ..."
}
```

| Campo | Significado | Cómo mostrarlo |
|---|---|---|
| `answer` | Respuesta principal | Burbuja del bot |
| `sections` | 0–6 tarjetas, ya ordenadas personal → udg → legal | Una tarjeta por sección, agrupadas/etiquetadas por `level` |
| `sections[].steps` | Lista de pasos (puede ser `[]`) | Lista numerada dentro de la tarjeta |
| `sections[].verified` | `false` = dato aún sin verificar con documento oficial | Mostrar insignia “por confirmar” cuando sea `false` |
| `in_scope` | `false` = tema fuera de alcance (ej. acoso, o pregunta no relacionada) | Burbuja con estilo de aviso; `sections` viene vacío |
| `mode` | `"retrieval"` (base local) o `"llm"` (redactado por IA) | Solo informativo; no cambia el formato |
| `disclaimer` | Aviso legal | Texto pequeño fijo bajo el chat |

**Notas importantes**
- `sections` puede venir vacío: renderiza solo `answer`.
- Si `in_scope` es `false` y el tema es acoso/hostigamiento, el mensaje es delicado: no lo trates como error; usa un color de atención (no rojo de error) y deja visible `answer`.
- Los textos pueden contener saltos de línea; respétalos.

### GET `/api/health`
`{"status":"ok","llm_enabled":false,"entries":10}` — úsalo para detectar si el servidor está vivo.

### Errores
- `422`: mensaje vacío o > 1000 caracteres (valida antes de enviar).
- Error de red / servidor caído: muestra “No se pudo conectar con el servidor. Intenta de nuevo.”

## 3. Recomendaciones de UI
1. Chat tipo mensajería: burbuja de usuario a la derecha, bot a la izquierda; indicador de “escribiendo…” mientras se espera.
2. Cada tarjeta de `sections` con color/icono distinto por nivel: **personal** (persona), **udg** (edificio/universidad), **legal** (balanza).
3. Chips de `suggested_questions` visibles al inicio y tras cada respuesta.
4. Responsive (los estudiantes lo usarán en celular).
5. Español en toda la interfaz. Accesible (contraste, foco de teclado, `aria-live` en el chat).
6. Mantén un arreglo `history` en memoria (no guardar datos personales en disco/localStorage: es un tema sensible).
7. Mostrar el `disclaimer` siempre.

## 4. Ejemplo mínimo de llamada
```js
const r = await fetch("/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message, history })
});
const data = await r.json();
```
(Si el HTML se abre fuera del servidor, usa la URL completa `http://127.0.0.1:8000/api/chat`.)

## 5. Lo que NO debes hacer
- No llames a ninguna API de IA desde el navegador ni pongas API keys en el frontend.
- No inventes texto del bot: todo viene de `answer` y `sections`.
- No modifiques el backend; si necesitas un campo nuevo, pídelo.
