// Briefing relay: fetches article pages (and Internet Archive copies) on behalf of
// YOUR briefing site only, so its reader view can show them cleanly.
// It never logs in anywhere: it sees exactly what an anonymous visitor sees.

const ALLOWED_ORIGINS = ["https://scadams1111.github.io"];
const MAX_BYTES = 6_000_000;
const PRIVATE_HOST = /^(localhost|0\.|127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1\]?$)/i;

export default {
  async fetch(request, env, ctx) {
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
