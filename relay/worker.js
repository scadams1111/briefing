// Briefing relay: fetches article pages (and Internet Archive copies) on behalf of
// YOUR briefing site only, so its reader view can show them cleanly.
// It never logs in anywhere: it sees exactly what an anonymous visitor sees.

const ALLOWED_ORIGINS = ["https://scadams1111.github.io"];
const MAX_BYTES = 6_000_000;
const PRIVATE_HOST = /^(localhost|0\.|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1\]?$)/i;

// Audio: GitHub serves release files as generic downloads, which iPhone won't play.
// /audio?url=<a briefing release file> streams it as real audio, with seeking (Range) support.
const AUDIO_PREFIX = "https://github.com/scadams1111/briefing/releases/download/";

async function audio(request) {
  const target = new URL(request.url).searchParams.get("url") || "";
  if (!target.toLowerCase().startsWith(AUDIO_PREFIX.toLowerCase()) || !/\.mp3$/i.test(target)) {
    return new Response("Not allowed", { status: 400 });
  }
  const headers = { "User-Agent": "BriefingRelay/1.0" };
  const range = request.headers.get("Range");
  if (range) headers["Range"] = range;
  const up = await fetch(target, { headers, redirect: "follow", cf: { cacheTtl: 86400, cacheEverything: true } });
  if (!up.ok && up.status !== 206) return new Response("Audio not found", { status: up.status });
  const h = new Headers();
  h.set("Content-Type", "audio/mpeg");
  h.set("Accept-Ranges", "bytes");
  h.set("Cache-Control", "public, max-age=86400");
  h.set("Access-Control-Allow-Origin", "*");
  for (const k of ["Content-Length", "Content-Range", "ETag", "Last-Modified"]) {
    const v = up.headers.get(k);
    if (v) h.set(k, v);
  }
  return new Response(request.method === "HEAD" ? null : up.body, { status: up.status, headers: h });
}

export default {
  async fetch(request, env, ctx) {
    if (new URL(request.url).pathname === "/audio" && (request.method === "GET" || request.method === "HEAD")) {
      return audio(request);
    }
    const origin = request.headers.get("Origin") || "";
    const allowed = ALLOWED_ORIGINS.includes(origin);
    const cors = {
      "Access-Control-Allow-Origin": allowed ? origin : ALLOWED_ORIGINS[0],
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Expose-Headers": "X-Final-URL",
      "Vary": "Origin",
    };
    const reply = (msg, status) => new Response(msg, { status, headers: cors });

    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "GET") return reply("Method not allowed", 405);
    if (!allowed) return reply("Forbidden", 403);

    let target;
    try { target = new URL(new URL(request.url).searchParams.get("url") || ""); }
    catch { return reply("Bad url", 400); }
    if (!/^https?:$/.test(target.protocol) || PRIVATE_HOST.test(target.hostname)) return reply("Not allowed", 400);

    const cache = caches.default;
    const key = new Request("https://relay.cache/" + encodeURIComponent(target.toString()));
    let res = await cache.match(key);
    if (!res) {
      const upstream = await fetch(target.toString(), {
        redirect: "follow",
        headers: {
          "User-Agent": "Mozilla/5.0 (compatible; BriefingReader/1.0; personal reader)",
          "Accept": "text/html,application/xhtml+xml",
          "Accept-Language": "en-US,en;q=0.9",
        },
      });
      const type = upstream.headers.get("Content-Type") || "";
      if (!/html|xml|json/i.test(type)) return reply("Unsupported content", 415);
      const body = await upstream.arrayBuffer();
      if (body.byteLength > MAX_BYTES) return reply("Too large", 413);
      res = new Response(body, {
        status: upstream.status,
        headers: { "Content-Type": type, "Cache-Control": "public, max-age=21600", "X-Final-URL": upstream.url },
      });
      if (upstream.ok) ctx.waitUntil(cache.put(key, res.clone()));
    }
    const out = new Response(res.body, res);
    for (const [k, v] of Object.entries(cors)) out.headers.set(k, v);
    return out;
  },
};
