// Avisos (notificaciones): revisa novedades cada 15 segundos, actualiza los
// contadores y muestra un aviso emergente. En las páginas de pedidos
// (data-recargar="1") recarga la página para mostrar el estado nuevo.
(function () {
    const config = document.getElementById("config-avisos");
    if (!config) return;
    const recargar = config.dataset.recargar === "1";
    const contadores = document.querySelectorAll("[data-contador-avisos]");
    const toast = document.getElementById("toast");
    const campana = document.getElementById("campana");          // Solo en escritorio.
    const lista = document.getElementById("lista-notificaciones");
    let ultimaId = null;

    function mostrarContador(n) {
        contadores.forEach(function (c) {
            c.textContent = n > 9 ? "9+" : n;
            c.hidden = n === 0;
        });
    }

    function mostrarToast(texto) {
        toast.textContent = texto;
        toast.hidden = false;
        clearTimeout(toast.temporizador);
        toast.temporizador = setTimeout(function () { toast.hidden = true; }, 6000);
    }

    async function revisar() {
        try {
            const r = await fetch("/notificaciones/resumen", { headers: { "Accept": "application/json" } });
            if (r.status === 401) { clearInterval(intervalo); return; }  // La sesión terminó: dejar de preguntar.
            if (!r.ok || !(r.headers.get("content-type") || "").includes("json")) return;
            const datos = await r.json();
            if (ultimaId !== null && datos.ultima_id > ultimaId) {
                if (recargar) { location.reload(); return; }
                mostrarToast(datos.ultima_texto);
                if (lista) lista.dataset.cargada = "false";
            }
            ultimaId = datos.ultima_id;
            mostrarContador(datos.sin_leer);
        } catch (e) { /* Sin conexión: se intenta en la próxima vuelta. */ }
    }

    // Lista desplegable de la campana (tienda y administrador).
    async function cargarLista() {
        const r = await fetch("/notificaciones", { headers: { "Accept": "text/html" } });
        const html = new DOMParser().parseFromString(await r.text(), "text/html");
        const items = html.querySelectorAll("#todas-notificaciones > li");
        lista.replaceChildren(...Array.from(items).slice(0, 8));
        if (!items.length) lista.innerHTML = '<li class="notificacion-vacia">No tienes notificaciones.</li>';
        lista.dataset.cargada = "true";
        mostrarContador(0);  // Abrir la lista las marca como leídas.
    }

    if (campana) {
        campana.addEventListener("toggle", function () {
            if (campana.open && lista.dataset.cargada !== "true") cargarLista();
        });
        document.addEventListener("click", function (e) {
            if (campana.open && !campana.contains(e.target)) campana.open = false;
        });
    }

    const intervalo = setInterval(revisar, 15000);
    revisar();
})();
