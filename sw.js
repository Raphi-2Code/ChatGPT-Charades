const CACHE_NAME = "ursina-charades-v23";

// ASSET_LIST_START
const ASSETS = [
  "./",
  "./README.md",
  "./brython.js",
  "./brython_stdlib.js",
  "./index.html",
  "./main.py",
  "./manifest.json",
  "./sw.js",
  "./ursina/__init__.py",
  "./ursina/button.py",
  "./ursina/camera.py",
  "./ursina/color.py",
  "./ursina/entity.py",
  "./ursina/input_handler.py",
  "./ursina/main.py",
  "./ursina/sequence.py",
  "./ursina/text.py",
  "./ursina.py"
];
// ASSET_LIST_END

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).then(() => {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => (key === CACHE_NAME ? null : caches.delete(key)))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(
      caches.match("./index.html").then((cached) => cached || fetch(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((cached) => {
      if (cached) {
        return cached;
      }

      return fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match("./index.html"));
    })
  );
});
