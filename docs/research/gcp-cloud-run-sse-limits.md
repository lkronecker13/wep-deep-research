# GCP Cloud Run SSE Streaming Limits and Configuration

**Research Date:** 2026-01-28
**Research Mode:** Standard
**Evidence Grade:** High (Official GCP documentation + community implementations)

## Executive Summary

Cloud Run 2nd generation fully supports Server-Sent Events (SSE) streaming with configurable timeouts up to 60 minutes. The request timeout applies to **total connection time**, not idle time. Application-level heartbeats (`: keepalive\n\n`) are recommended every 30 seconds to prevent intermediate proxy buffering, but do **not** reset Cloud Run's timeout. Critical configuration requirements include disabling proxy buffering and implementing client reconnection logic.

---

## 1. Maximum SSE Connection Duration

### Timeout Limits

| Configuration | Value | Source |
|---------------|-------|--------|
| **Default timeout** | 5 minutes (300s) | [Cloud Run docs](https://docs.cloud.google.com/run/docs/configuring/request-timeout) |
| **Maximum timeout** | 60 minutes (3600s) | [Cloud Run docs](https://docs.cloud.google.com/run/docs/configuring/request-timeout) |
| **Minimum timeout** | 1 second | [Cloud Run docs](https://docs.cloud.google.com/run/docs/configuring/request-timeout) |

### Timeout Behavior

**Critical Finding:** The timeout represents the **total connection duration**, not idle time between events.

From the [official documentation](https://docs.cloud.google.com/run/docs/configuring/request-timeout):

> "The timeout specifies the time within which a response must be returned by services deployed to Cloud Run. When the timeout period expires, the network connection to the service will be closed and an error 504 is returned."

**Container Behavior:** The container instance continues running after timeout—it is not terminated. This means server-side processing may continue even after the client connection closes.

### Configuration Example

```bash
gcloud run deploy my-service \
  --image gcr.io/project/image \
  --platform managed \
  --region us-central1 \
  --timeout=3600 \
  --allow-unauthenticated
```

Or via YAML service specification:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: my-sse-service
spec:
  template:
    spec:
      timeoutSeconds: 3600  # 60 minutes
      containers:
      - image: gcr.io/project/image
        ports:
        - containerPort: 8080
```

---

## 2. Request Timeout: Idle vs Total Connection Time

### Definitive Answer

**The request timeout applies to TOTAL connection time, not idle time.**

Evidence from [WebSocket documentation](https://docs.cloud.google.com/run/docs/triggering/websockets) (applicable to all streaming protocols):

> "WebSockets streams are HTTP requests, which are still subject to the request timeout configured for your Cloud Run service, so you need to increase the request timeout period to the maximum duration you would like to keep the WebSockets stream open, for example 60 minutes."

**Key Implication:** If you configure a 10-minute timeout, the connection will be terminated after 10 minutes regardless of whether events are actively being sent. Heartbeats do not extend or reset this timer.

### Load Balancer Idle Timeout

There is a separate consideration for truly idle connections: The default load balancer has an idle timeout of 30 seconds for connections to backend services. However, this is distinct from the service-level request timeout.

---

## 3. SSE Heartbeat Comments and Timeout Behavior

### Do Heartbeats Reset Cloud Run's Timer?

**Answer: NO**

Heartbeats serve a different purpose: preventing **intermediate proxy buffering**, not extending Cloud Run's request timeout.

### Why Heartbeats Are Still Critical

From [community research](https://medium.com/@moali314/server-sent-events-a-comprehensive-guide-e4b15d147576):

> "The HTTP/1.1 specification allows proxies to close idle connections after 60 seconds."

Heartbeats prevent:
1. **Proxy buffering** - Ensures proxies flush events immediately rather than buffering
2. **Intermediate timeout** - Prevents CDNs, load balancers, or reverse proxies from closing idle connections
3. **Connection staleness** - Keeps TCP connection alive through intermediate hops

### Recommended Heartbeat Interval

**30 seconds** is the industry-standard recommendation.

From [production guidance](https://mcpcat.io/guides/building-streamablehttp-mcp-server/):

> "Long-running operations trigger SSE timeouts when intermediate proxies buffer responses... The fix is to send periodic heartbeats every 30 seconds."

### Implementation Example (Python/FastAPI)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

@app.get("/events")
async def sse_endpoint():
    async def event_generator():
        try:
            while True:
                # Send heartbeat every 30 seconds
                yield ": keepalive\n\n"
                await asyncio.sleep(30)

                # Send actual events when available
                if has_event():
                    event_data = get_next_event()
                    yield f"data: {event_data}\n\n"
        except asyncio.CancelledError:
            # Client disconnected
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

### SSE Heartbeat Format

Standard SSE heartbeat is a comment line:

```
: keepalive\n\n
```

Or a named event:

```
event: ping\ndata: {}\n\n
```

Both formats are ignored by EventSource clients but keep the connection active.

---

## 4. Recommended Configuration for Long-Running SSE

### For 30-180 Second Connections

#### Cloud Run Service Configuration

```bash
gcloud run deploy research-service \
  --image gcr.io/project/research-api \
  --region us-central1 \
  --timeout=600 \          # 10 minutes (covers 180s + overhead)
  --cpu=2 \                # Adequate CPU for streaming
  --memory=1Gi \
  --max-instances=100 \    # Scale for concurrent streams
  --session-affinity       # Improve reconnection routing
```

**Rationale:**
- **10-minute timeout**: Provides buffer beyond 180s maximum expected duration
- **Session affinity**: Improves (but doesn't guarantee) client reconnection to same instance
- **Adequate resources**: Streaming connections hold instances active and incur CPU billing

#### Application Configuration

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
from typing import AsyncGenerator

app = FastAPI()

HEARTBEAT_INTERVAL = 30  # seconds
MAX_DURATION = 180       # seconds

@app.get("/research")
async def research_stream(request: Request):
    async def generate_events() -> AsyncGenerator[str, None]:
        start_time = asyncio.get_event_loop().time()
        last_heartbeat = start_time

        try:
            while True:
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - start_time

                # Enforce maximum duration
                if elapsed > MAX_DURATION:
                    yield "event: complete\ndata: {}\n\n"
                    break

                # Check for client disconnect
                if await request.is_disconnected():
                    break

                # Send heartbeat if needed
                if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
                    yield ": keepalive\n\n"
                    last_heartbeat = current_time

                # Send actual research events
                if has_update():
                    event = get_next_update()
                    yield f"data: {event}\n\n"

                await asyncio.sleep(1)  # Check for events every second

        except asyncio.CancelledError:
            pass  # Client disconnected

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

#### Key Implementation Details

1. **Heartbeat Management**
   - Send `: keepalive\n\n` every 30 seconds
   - Track last heartbeat time to avoid over-sending
   - Heartbeats count as data transfer (prevents proxy timeout)

2. **Client Disconnect Detection**
   - Use `await request.is_disconnected()` (FastAPI)
   - Gracefully handle `asyncio.CancelledError`
   - Clean up resources when client disconnects

3. **Maximum Duration Enforcement**
   - Track connection start time
   - Enforce hard limit (180s for research use case)
   - Send completion event before closing

4. **Response Headers**
   - `Content-Type: text/event-stream` - Required for SSE
   - `Cache-Control: no-cache` - Prevent caching
   - `X-Accel-Buffering: no` - Disable nginx/proxy buffering
   - `Connection: keep-alive` - Maintain persistent connection

---

## 5. Proxy Buffering Configuration

### The Critical Problem

Many proxies (nginx, Cloudflare, API gateways) buffer responses by default, which breaks SSE streaming. Events accumulate in proxy buffers and are not flushed to clients until buffer thresholds are met.

### Solution 1: Application-Level Header

**Recommended approach** - Works across most proxy configurations:

```python
headers = {
    "X-Accel-Buffering": "no"
}
```

From [community troubleshooting](https://medium.com/@wang645788/troubleshooting-server-sent-events-sse-in-a-multi-service-architecture-5084ce155ea0):

> "Setting the header `X-Accel-Buffering: no` tells Nginx to not use buffering for this response."

### Solution 2: Nginx Configuration

If you control the reverse proxy:

```nginx
location /api/stream {
    proxy_pass http://backend;

    # Disable buffering for SSE
    proxy_buffering off;
    proxy_cache off;

    # Disable gzip compression
    gzip off;

    # Use HTTP/1.1 for chunked encoding
    proxy_http_version 1.1;

    # Required headers
    proxy_set_header Connection "";
    proxy_set_header X-Real-IP $remote_addr;

    # Timeouts
    proxy_read_timeout 3600s;
    proxy_connect_timeout 75s;
}
```

From [DigitalOcean community guidance](https://www.digitalocean.com/community/questions/nginx-optimization-for-server-sent-events-sse):

> "For Server-Sent Events (SSE) and streaming responses through nginx proxies, disabling proxy buffering is very important."

### Cloudflare Considerations

If using Cloudflare:
- Enterprise plan required for full control
- Set `X-Accel-Buffering: no` header
- Consider disabling Cloudflare for streaming endpoints

---

## 6. Caveats and Limitations

### Instance Billing Impact

From [WebSocket documentation](https://docs.cloud.google.com/run/docs/triggering/websockets):

> "A Cloud Run instance that has any open WebSocket connection is considered active, so CPU is allocated and the service is billed as instance-based billing."

**This applies to SSE as well:**
- Active SSE connections hold instances in billable state
- CPU is allocated for the entire connection duration
- Long-running streams can significantly increase costs

**Cost Mitigation:**
1. Enforce maximum connection duration (e.g., 180s)
2. Use minimum instances only if predictable traffic
3. Monitor connection count and duration
4. Consider WebSocket for bidirectional communication (same cost, more efficient)

### Container Shutdown Behavior

From [Cloud Run documentation](https://docs.cloud.google.com/run/docs/configuring/request-timeout):

> "Unless a container instance must be kept idle due to the minimum number of container instances configuration setting, it will not be kept idle for longer than 15 minutes."

**Implication:** If no requests arrive for 15 minutes, the instance may be shut down. New connections will experience cold start latency.

### Client Reconnection Required

For timeouts exceeding 15 minutes, [Google recommends](https://docs.cloud.google.com/run/docs/configuring/request-timeout):

> "Implementing retry logic and ensuring services are tolerant to clients re-connecting in case the connection is lost."

**Best Practice:** Always implement client-side reconnection with exponential backoff:

```javascript
const connectSSE = (url, maxRetries = 5) => {
  let retries = 0;
  let eventSource;

  const connect = () => {
    eventSource = new EventSource(url);

    eventSource.onopen = () => {
      console.log('SSE connected');
      retries = 0; // Reset on success
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();

      if (retries < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retries), 30000);
        console.log(`Reconnecting in ${delay}ms...`);
        setTimeout(connect, delay);
        retries++;
      }
    };

    eventSource.onmessage = (event) => {
      console.log('Event:', event.data);
    };
  };

  connect();
  return eventSource;
};

// Usage
const stream = connectSSE('/api/research');
```

### Multi-Instance Synchronization

If scaling beyond 1 instance, you'll need external synchronization for broadcast events:

From [Cloud Run WebSocket docs](https://docs.cloud.google.com/run/docs/triggering/websockets):

> "For scaling across instances, use external systems like Redis Pub/Sub or Firestore real-time updates to keep instances synchronized."

**Recommended Approach for Multi-Instance SSE:**

```python
import redis.asyncio as redis
from fastapi import FastAPI

app = FastAPI()
redis_client = redis.Redis(host='redis-host', decode_responses=True)

@app.get("/events")
async def events():
    async def subscribe_and_stream():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('research_events')

        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield f"data: {message['data']}\n\n"

    return StreamingResponse(
        subscribe_and_stream(),
        media_type="text/event-stream"
    )
```

### Known Issues from Community

From [community discussions](https://discuss.google.dev/t/server-sent-events-on-cloud-run-not-working/124831):

1. **External Load Balancers:** Can cause buffering problems (use `X-Accel-Buffering: no`)
2. **HTTP/2:** May cause issues with some SSE clients (configure for HTTP/1.1 if needed)
3. **Cold Starts:** First connection after idle period experiences latency (use min instances if critical)

---

## 7. Production Recommendations

### Quick Reference Configuration Matrix

| Duration | Timeout | Heartbeat | Min Instances | Cost Impact |
|----------|---------|-----------|---------------|-------------|
| 0-30s    | 120s    | Not needed | 0 | Low |
| 30-180s  | 600s    | 30s        | 0-1 | Medium |
| 3-10min  | 900s    | 30s        | 1-2 | High |
| 10-60min | 3600s   | 30s        | 2-5 | Very High |

### Checklist for Production Deployment

- [ ] Set request timeout to at least 2x expected maximum duration
- [ ] Implement 30-second heartbeat mechanism
- [ ] Add `X-Accel-Buffering: no` header
- [ ] Implement client reconnection with exponential backoff
- [ ] Monitor connection duration and count
- [ ] Set up alerts for timeout spikes
- [ ] Test with production load balancer/CDN configuration
- [ ] Document expected connection duration in service SLO
- [ ] Implement graceful shutdown for long-running connections
- [ ] Add connection count metrics to dashboards

### Monitoring Queries (Cloud Monitoring)

```yaml
# Connection duration percentiles
fetch cloud_run_revision
| metric 'run.googleapis.com/request_latencies'
| filter resource.service_name == 'research-service'
| group_by 5m, [percentile(value.request_latencies, [50, 90, 99])]

# Active connection count
fetch cloud_run_revision
| metric 'run.googleapis.com/container/instance_count'
| filter resource.service_name == 'research-service'
| group_by 1m, [sum(value.instance_count)]

# Timeout error rate
fetch cloud_run_revision
| metric 'run.googleapis.com/request_count'
| filter resource.service_name == 'research-service'
      && metric.response_code_class == '5xx'
| group_by 5m, [rate()]
```

---

## 8. Evidence Quality Assessment

| Source Type | Examples | Grade | Notes |
|-------------|----------|-------|-------|
| **Official GCP Docs** | [Request Timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout), [WebSockets](https://docs.cloud.google.com/run/docs/triggering/websockets) | A+ | Authoritative, current (2026) |
| **Google Blog** | [Server Streaming Support](https://cloud.google.com/blog/products/serverless/cloud-run-now-supports-http-grpc-server-streaming) | A | Official announcement |
| **Community Examples** | [cloud-run-sse repo](https://github.com/micahjsmith/cloud-run-sse) | B+ | Working implementation |
| **Production Guides** | [MCP Server Guide](https://mcpcat.io/guides/building-streamablehttp-mcp-server/) | B | Recent (2025), practical |
| **Developer Forums** | [Google Developer Forums](https://discuss.google.dev/t/server-sent-events-on-cloud-run-not-working/124831) | C+ | Real-world issues, unverified |

### Limitations of This Research

1. **No official SSE-specific documentation** - Most guidance extrapolated from WebSocket docs
2. **Heartbeat behavior not explicitly documented** - Inferred from WebSocket and HTTP streaming behavior
3. **Multi-instance coordination** - Limited official guidance; mostly community solutions
4. **Cost modeling** - No published cost calculator for long-running streaming connections

### Recommended Follow-Up

- **Load test** with production traffic patterns to validate timeout behavior
- **Monitor** actual connection durations vs configured timeouts in production
- **Engage Google Support** for enterprise workloads requiring >60min connections
- **Benchmark** cost impact of streaming vs polling alternatives

---

## Sources

### Official Documentation
- [Configure request timeout for services | Cloud Run Documentation](https://docs.cloud.google.com/run/docs/configuring/request-timeout)
- [Using WebSockets | Cloud Run Documentation](https://docs.cloud.google.com/run/docs/triggering/websockets)
- [Troubleshoot Cloud Run issues | Cloud Run Documentation](https://docs.cloud.google.com/run/docs/troubleshooting)
- [Cloud Run now supports HTTP/gRPC server streaming | Google Cloud Blog](https://cloud.google.com/blog/products/serverless/cloud-run-now-supports-http-grpc-server-streaming)

### Community Resources
- [cloud-run-sse GitHub Repository](https://github.com/micahjsmith/cloud-run-sse)
- [Build StreamableHTTP MCP Servers - Production Guide | MCPcat](https://mcpcat.io/guides/building-streamablehttp-mcp-server/)
- [Server Sent Events on Cloud Run not working - Google Developer Forums](https://discuss.google.dev/t/server-sent-events-on-cloud-run-not-working/124831)
- [Server-Sent Events: A Comprehensive Guide | Medium](https://medium.com/@moali314/server-sent-events-a-comprehensive-guide-e4b15d147576)

### Proxy Configuration Guidance
- [Troubleshooting Server-Sent Events (SSE) in a Multi-Service Architecture | Medium](https://medium.com/@wang645788/troubleshooting-server-sent-events-sse-in-a-multi-service-architecture-5084ce155ea0)
- [NGINX Optimization for Server-Sent Events (SSE) | DigitalOcean](https://www.digitalocean.com/community/questions/nginx-optimization-for-server-sent-events-sse)
- [Surviving SSE Behind Nginx Proxy Manager | Medium](https://medium.com/@dsherwin/surviving-sse-behind-nginx-proxy-manager-npm-a-real-world-deep-dive-69c5a6e8b8e5)

---

**Research completed:** 2026-01-28
**Confidence level:** High for documented features, Medium for production edge cases
**Recommended refresh:** Q2 2026 (check for Cloud Run updates)
