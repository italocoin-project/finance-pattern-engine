/* Finance Pattern Engine — offline shell and stale-data fallback. */
const VERSION = "fpe-shell-v1";
const SHELL_CACHE = VERSION;
const DATA_CACHE = "fpe-data-v1";
const SHELL = [
  "./",
  "./index.html",
  "./markets.html",
  "./coin.html",
  "./privacy.html",
  "./terms.html",
  "./offline.html",
  "./manifest.webmanifest",
  "./assets/fpe-icon.svg",
  "./guide/confrontare-exchange.html",
  "./guide/exchange-e-blockchain.html",
  "./guide/leggere-storico-crypto.html",
  "./guide/volumi-spread-liquidita.html"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(cache => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys
        .filter(key => key.startsWith("fpe-") && ![SHELL_CACHE, DATA_CACHE].includes(key))
        .map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.endsWith("/data/market/cmc-market.json")) {
    event.respondWith((async () => {
      const cache = await caches.open(DATA_CACHE);
      try {
        const response = await fetch(request);
        if (response.ok) await cache.put(request, response.clone());
        return response;
      } catch (error) {
        return (await cache.match(request)) || new Response(
          JSON.stringify({error: "offline", coins: []}),
          {status: 503, headers: {"Content-Type": "application/json; charset=utf-8"}}
        );
      }
    })());
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const response = await fetch(request);
        if (response.ok) {
          const cache = await caches.open(SHELL_CACHE);
          const cleanUrl = new URL(url.pathname, self.location.origin);
          await cache.put(cleanUrl.href, response.clone());
        }
        return response;
      } catch (error) {
        const cache = await caches.open(SHELL_CACHE);
        const cleanUrl = new URL(url.pathname, self.location.origin);
        return (await cache.match(cleanUrl.href)) || (await cache.match("./offline.html"));
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cache = await caches.open(SHELL_CACHE);
    const cached = await cache.match(request);
    if (cached) return cached;
    try {
      const response = await fetch(request);
      if (response.ok && response.type === "basic") await cache.put(request, response.clone());
      return response;
    } catch (error) {
      return cached || Response.error();
    }
  })());
});
