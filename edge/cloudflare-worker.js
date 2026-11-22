/**
 * TalentAI Edge Router & Reverse Proxy (Cloudflare Worker)
 * 
 * Solves Cross-Region Latency Overhead:
 * 1. TLS 1.3 Termination at local Edge POP (Mumbai BOM, Delhi DEL, Bangalore BLR) in <15ms.
 * 2. Routes requests to Render origin over Cloudflare's private global fiber network.
 * 3. Edge-caches static/read-only responses (resumes, jobs, health checks) with stale-while-revalidate.
 * 4. Zero-buffer passthrough for Server-Sent Events (SSE) typewriter streaming.
 * 5. Handles CORS preflight directly at the edge in <2ms without hitting origin server.
 */

// Default Render origin backend URL (can be overridden via environment variable)
const DEFAULT_ORIGIN = "https://talentai-recruitment.onrender.com";

// Endpoints suitable for edge caching (GET requests)
const CACHEABLE_ROUTES = [
  /\/api\/v1\/candidates\/\d+\/resume$/,
  /\/api\/v1\/jobs$/,
  /\/api\/v1\/health$/,
  /\/api\/v1\/system\/region-telemetry$/,
  /\/api\/v1\/search\/cache\/stats$/
];

export default {
  async fetch(request, env, ctx) {
    const startTime = Date.now();
    const url = new URL(request.url);
    const originBackend = (env?.ORIGIN_BACKEND_URL || DEFAULT_ORIGIN).replace(/\/+$/, "");

    // 1. Instant Edge CORS Preflight Response (<2ms)
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
          "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key, Accept",
          "Access-Control-Max-Age": "86400",
          "X-Edge-POP": request.cf?.colo || "EDGE",
          "X-Edge-Latency-Ms": `${Date.now() - startTime}`
        }
      });
    }

    // 2. Edge Cache Lookup for read-only static endpoints
    const cache = caches.default;
    const isCacheable = request.method === "GET" && CACHEABLE_ROUTES.some(pattern => pattern.test(url.pathname));

    if (isCacheable) {
      const cachedResponse = await cache.match(request);
      if (cachedResponse) {
        const responseWithHeaders = new Response(cachedResponse.body, cachedResponse);
        responseWithHeaders.headers.set("X-Edge-Cache", "HIT");
        responseWithHeaders.headers.set("X-Edge-POP", request.cf?.colo || "EDGE");
        responseWithHeaders.headers.set("X-Edge-Latency-Ms", `${Date.now() - startTime}`);
        return responseWithHeaders;
      }
    }

    // 3. Construct Origin Request URL
    const targetUrl = new URL(url.pathname + url.search, originBackend);
    const originHeaders = new Headers(request.headers);
    
    // Inject Cloudflare client location headers for backend observability
    originHeaders.set("X-Forwarded-Host", url.host);
    originHeaders.set("X-Forwarded-Proto", url.protocol.replace(":", ""));
    originHeaders.set("X-Client-Country", request.cf?.country || "IN");
    originHeaders.set("X-Client-City", request.cf?.city || "Unknown");
    originHeaders.set("X-Edge-Colo", request.cf?.colo || "BOM");

    const isStreamingRequest = url.pathname.includes("/evaluate/stream");

    try {
      const originResponse = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: originHeaders,
        body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
        redirect: "follow"
      });

      // 4. Handle Server-Sent Events (SSE) Streaming without buffer delays
      if (isStreamingRequest || originResponse.headers.get("content-type")?.includes("text/event-stream")) {
        const sseHeaders = new Headers(originResponse.headers);
        sseHeaders.set("Access-Control-Allow-Origin", "*");
        sseHeaders.set("Cache-Control", "no-cache, no-transform");
        sseHeaders.set("X-Accel-Buffering", "no");
        sseHeaders.set("X-Edge-POP", request.cf?.colo || "EDGE");
        sseHeaders.set("X-Edge-Stream", "PASSTHROUGH");

        return new Response(originResponse.body, {
          status: originResponse.status,
          headers: sseHeaders
        });
      }

      // 5. Clone and Cache eligible responses at the Edge
      const responseHeaders = new Headers(originResponse.headers);
      responseHeaders.set("Access-Control-Allow-Origin", "*");
      responseHeaders.set("X-Edge-POP", request.cf?.colo || "EDGE");
      responseHeaders.set("X-Edge-Latency-Ms", `${Date.now() - startTime}`);

      if (isCacheable && originResponse.status === 200) {
        responseHeaders.set("Cache-Control", "public, max-age=60, s-maxage=300, stale-while-revalidate=600");
        responseHeaders.set("X-Edge-Cache", "MISS");

        const responseToCache = new Response(originResponse.body, {
          status: originResponse.status,
          headers: responseHeaders
        });

        // Store asynchronously without blocking response
        ctx.waitUntil(cache.put(request, responseToCache.clone()));
        return responseToCache;
      }

      return new Response(originResponse.body, {
        status: originResponse.status,
        headers: responseHeaders
      });

    } catch (err) {
      return new Response(JSON.stringify({
        error: "Edge proxy gateway error",
        message: err.message,
        edge_pop: request.cf?.colo || "BOM",
        target: targetUrl.toString()
      }), {
        status: 502,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "X-Edge-Error": "GATEWAY_TIMEOUT"
        }
      });
    }
  },

  /**
   * Cloudflare Cron Trigger Keep-Alive Daemon
   * Fires every 10 minutes to prevent Render free-tier inactivity sleep.
   */
  async scheduled(event, env, ctx) {
    const originBackend = (env?.ORIGIN_BACKEND_URL || DEFAULT_ORIGIN).replace(/\/+$/, "");
    const healthUrl = `${originBackend}/health`;
    try {
      const resp = await fetch(healthUrl, { method: "GET" });
      console.log(`[Keep-Alive Cron] Pinged ${healthUrl} - Status: ${resp.status}`);
    } catch (err) {
      console.error(`[Keep-Alive Cron] Failed to ping ${healthUrl}: ${err.message}`);
    }
  }
};
