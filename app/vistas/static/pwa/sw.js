// Service worker de Bee (app instalable).
// - Las páginas siempre se piden al servidor (tienen datos y tokens de cada
//   usuario, así que no se guardan). Sin internet se muestra /offline.
// - Los íconos de la app se guardan para que abra rápido.
const VERSION = "bee-v2";
const GUARDAR = ["/offline", "/static/pwa/icono-192.png", "/static/pwa/icono-512.png"];

self.addEventListener("install", (evento) => {
    evento.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(GUARDAR)));
    self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
    evento.waitUntil(
        caches.keys().then((nombres) =>
            Promise.all(nombres.filter((n) => n !== VERSION).map((n) => caches.delete(n)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (evento) => {
    const pedido = evento.request;
    if (pedido.method !== "GET") return;

    if (pedido.mode === "navigate") {
        evento.respondWith(fetch(pedido).catch(() => caches.match("/offline")));
        return;
    }
    const url = new URL(pedido.url);
    if (url.origin === location.origin && url.pathname.startsWith("/static/pwa/")) {
        evento.respondWith(caches.match(pedido).then((guardado) => guardado || fetch(pedido)));
    }
});

// ---------- Avisos push ("🐝 Tu pedido está listo") ----------
self.addEventListener("push", (evento) => {
    let datos = {};
    try { datos = evento.data ? evento.data.json() : {}; } catch (e) { datos = { cuerpo: evento.data && evento.data.text() }; }
    evento.waitUntil(
        self.registration.showNotification(datos.titulo || "Bee", {
            body: datos.cuerpo || "Tienes una novedad en tus pedidos.",
            icon: "/static/pwa/icono-192.png",
            badge: "/static/pwa/icono-192.png",
            data: { url: datos.url || "/app" },
            vibrate: [120, 60, 120],
        })
    );
});

// Al tocar el aviso se abre la app (o se enfoca si ya estaba abierta).
self.addEventListener("notificationclick", (evento) => {
    evento.notification.close();
    const url = new URL(evento.notification.data.url, location.origin).href;
    evento.waitUntil(
        self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((ventanas) => {
            for (const v of ventanas) {
                if (v.url.startsWith(location.origin) && "focus" in v) { v.navigate(url); return v.focus(); }
            }
            return self.clients.openWindow(url);
        })
    );
});
