// Frontend del Orientador UDG - conectado al backend (autómata de estados)
// Usa los IDs de index.html y las clases de style.css

const $ = (id) => document.getElementById(id);
const listaMensajes = $("chat-messages");
const zonaChat = document.querySelector(".chat-container");
const escribiendo = $("typing-indicator");
const chips = $("suggested-chips");
const form = $("chat-form");
const input = $("user-input");
const botonEnviar = $("send-btn");

let estado = null;          // estado actual del autómata (lo devuelve el backend)
let sugeridas = [];         // preguntas sugeridas de /api/config
let ocupado = false;

// ---------- utilidades ----------
function el(tag, clase, texto) {
  const e = document.createElement(tag);
  if (clase) e.className = clase;
  if (texto !== undefined) e.textContent = texto;
  return e;
}

function bajar() {
  zonaChat.scrollTop = zonaChat.scrollHeight;
}

function ponerEstado(tipo, texto) {
  $("status-text").textContent = texto;
  const punto = document.querySelector(".status-dot");
  punto.classList.remove("online", "offline");
  if (tipo) punto.classList.add(tipo);
}

// ---------- mensajes ----------
function tarjeta(s) {
  const c = el("div", "level-card " + s.level);

  const cab = el("div", "card-header");
  cab.appendChild(el("span", "card-level-label", s.level_label));
  if (!s.verified) cab.appendChild(el("span", "badge-unverified", "Por confirmar"));
  c.appendChild(cab);

  c.appendChild(el("div", "card-title", s.title));
  c.appendChild(el("div", "card-content", s.content));

  if (s.steps && s.steps.length) {
    const ol = el("ol", "card-steps");
    s.steps.forEach((p) => ol.appendChild(el("li", "", p)));
    c.appendChild(ol);
  }
  return c;
}

function agregarMensaje(rol, texto, extra = {}) {
  const m = el("div", "message " + rol + (extra.fueraDeAlcance ? " out-of-scope" : ""));
  const burbuja = el("div", "bubble", texto);
  burbuja.style.whiteSpace = "pre-line";
  m.appendChild(burbuja);

  if (extra.sections && extra.sections.length) {
    const cont = el("div", "sections-container");
    extra.sections.forEach((s) => cont.appendChild(tarjeta(s)));
    m.appendChild(cont);
  }
  listaMensajes.appendChild(m);
  bajar();
}

// ---------- botones (opciones del autómata o sugerencias) ----------
function ponerChips(opciones) {
  chips.innerHTML = "";
  const lista = opciones && opciones.length ? opciones : sugeridas;
  document.querySelector(".suggested-title").textContent =
    opciones && opciones.length ? "Elige una opción o escribe tu duda:" : "Sugerencias:";
  lista.forEach((t) => {
    const b = el("button", "chip-btn", t);
    b.type = "button";
    b.onclick = () => enviar(t);
    chips.appendChild(b);
  });
}

// ---------- enviar ----------
async function enviar(texto) {
  texto = texto.trim();
  if (!texto || ocupado) return;
  ocupado = true;
  botonEnviar.disabled = true;

  agregarMensaje("user", texto);
  input.value = "";
  escribiendo.classList.remove("hidden");
  bajar();

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: texto, state: estado }),
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();

    estado = data.state;
    escribiendo.classList.add("hidden");
    agregarMensaje("assistant", data.answer, {
      sections: data.sections,
      fueraDeAlcance: !data.in_scope,
    });
    ponerChips(data.options);
    if (data.disclaimer) $("disclaimer-text").textContent = data.disclaimer;
    ponerEstado("online", "En línea");
  } catch (e) {
    escribiendo.classList.add("hidden");
    agregarMensaje("assistant", "No se pudo conectar con el servidor. Intenta de nuevo.", {
      fueraDeAlcance: true,
    });
    ponerEstado("offline", "Sin conexión");
  } finally {
    ocupado = false;
    botonEnviar.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (ev) => {
  ev.preventDefault();       // evita que la página se recargue
  enviar(input.value);
});

// ---------- inicio ----------
async function iniciar() {
  try {
    const r = await fetch("/api/config");
    if (!r.ok) throw new Error("HTTP " + r.status);
    const cfg = await r.json();

    $("assistant-title").textContent = cfg.assistant_name;
    $("disclaimer-text").textContent = cfg.disclaimer;
    sugeridas = cfg.suggested_questions || [];
    estado = cfg.start.state;

    agregarMensaje("assistant", cfg.start.answer);
    ponerChips(cfg.start.options);
    ponerEstado("online", "En línea");
  } catch (e) {
    ponerEstado("offline", "Sin conexión");
    agregarMensaje(
      "assistant",
      "No se pudo conectar con el servidor. Revisa que esté encendido y abre esta página desde http://127.0.0.1:8000",
      { fueraDeAlcance: true }
    );
  }
}

iniciar();