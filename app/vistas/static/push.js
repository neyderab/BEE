// Botón «Activar avisos»: pide permiso y registra este celular para recibir
// notificaciones push aunque la app esté cerrada.
(function () {
    const tarjetas = document.querySelectorAll("[data-avisos-push]");
    if (!tarjetas.length) return;
    const token = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
    const soporta = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
    const esIphone = /iPhone|iPad|iPod/.test(navigator.userAgent);

    function claveBinaria(base64) {
        const relleno = "=".repeat((4 - (base64.length % 4)) % 4);
        const texto = atob((base64 + relleno).replace(/-/g, "+").replace(/_/g, "/"));
        return Uint8Array.from(texto, (c) => c.charCodeAt(0));
    }

    async function enviar(url, datos) {
        const r = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
            body: JSON.stringify(datos),
        });
        if (!r.ok) throw new Error("respuesta " + r.status);
    }

    async function suscripcionActual() {
        const registro = await navigator.serviceWorker.ready;
        return registro.pushManager.getSubscription();
    }

    function pintar(estado) {
        tarjetas.forEach(function (t) {
            const texto = t.querySelector("[data-push-texto]");
            const boton = t.querySelector("[data-push-boton]");
            t.hidden = false;
            t.dataset.estado = estado;
            boton.hidden = false;
            boton.disabled = false;
            if (estado === "activo") {
                texto.textContent = "✅ Avisos activados en este dispositivo.";
                boton.textContent = "Desactivar";
                boton.classList.add("boton-secundario");
            } else if (estado === "inactivo") {
                texto.textContent = t.dataset.descripcion;
                boton.textContent = "Activar avisos";
                boton.classList.remove("boton-secundario");
            } else if (estado === "bloqueado") {
                texto.textContent = "Bloqueaste los avisos de Bee. Actívalos en los ajustes del navegador o del celular.";
                boton.hidden = true;
            } else if (estado === "instalar") {
                texto.textContent = "En iPhone, primero instala la app: botón Compartir → «Agregar a pantalla de inicio». Luego actívalos desde la app.";
                boton.hidden = true;
            } else {
                t.hidden = true;  // Este navegador no tiene avisos push.
            }
        });
    }

    async function revisar() {
        if (!soporta) return pintar(esIphone ? "instalar" : "no-soporta");
        if (Notification.permission === "denied") return pintar("bloqueado");
        pintar((await suscripcionActual()) ? "activo" : "inactivo");
    }

    async function alternar(boton) {
        boton.disabled = true;
        try {
            const actual = await suscripcionActual();
            if (actual) {
                await enviar("/push/desuscribir", { endpoint: actual.endpoint });
                await actual.unsubscribe();
            } else {
                if ((await Notification.requestPermission()) !== "granted") return revisar();
                const { clave } = await (await fetch("/push/clave")).json();
                const registro = await navigator.serviceWorker.ready;
                const nueva = await registro.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: claveBinaria(clave) });
                await enviar("/push/suscribir", nueva.toJSON());
            }
        } catch (error) {
            alert("No se pudieron cambiar los avisos. Inténtalo de nuevo.");
        }
        revisar();
    }

    tarjetas.forEach(function (t) {
        t.querySelector("[data-push-boton]").addEventListener("click", function () { alternar(this); });
    });
    revisar();
})();
