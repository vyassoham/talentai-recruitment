# TalentAI Cloudflare Edge Router & Reverse Proxy

This Cloudflare Worker eliminates **cross-region network latency** by terminating TLS handshakes at local Edge POPs across India (Mumbai, Delhi, Bangalore) in **<15ms**, and routing origin traffic over Cloudflare's private optical network directly to the Render backend.

---

### Features

1. **Sub-15ms Local Edge POP TLS Handshake:**
   - Instead of the recruiter's browser in India completing a 150ms roundtrip TLS handshake to Render (US/EU), the handshake completes locally in Mumbai (`BOM`), Delhi (`DEL`), or Bangalore (`BLR`).
2. **Edge Cache (Stale-While-Revalidate):**
   - Automatically edge-caches high-frequency read requests (`/api/v1/jobs`, `/api/v1/candidates/{id}/resume`, `/api/v1/system/region-telemetry`).
3. **SSE Streaming Passthrough:**
   - Server-Sent Events typewriter evaluation (`/evaluate/stream`) streams raw tokens without edge buffering.
4. **Instant Edge CORS Preflight (<2ms):**
   - `OPTIONS` preflight requests are answered immediately at the edge with `204 No Content` without touching Render origin.

---

### Deployment (1 Command)

1. Navigate to the `edge` directory:
   ```bash
   cd edge
   ```
2. Log in to Cloudflare (Free Tier):
   ```bash
   npx wrangler login
   ```
3. Deploy the worker:
   ```bash
   npx wrangler deploy
   ```
4. Update `NEXT_PUBLIC_API_URL` in your frontend environment variables to your Cloudflare Worker URL:
   ```
   NEXT_PUBLIC_API_URL=https://talentai-edge-proxy.<your-subdomain>.workers.dev/api/v1
   ```
