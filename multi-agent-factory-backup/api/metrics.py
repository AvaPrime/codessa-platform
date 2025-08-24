from prometheus_client import Counter, Histogram, generate_latest

REQUESTS = Counter("api_requests_total", "API requests", ["method", "path", "status"])
LATENCY = Histogram("api_request_latency_seconds", "API latency", ["method", "path"])

def instrument(app):
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        method = request.method
        path = request.url.path
        with LATENCY.labels(method=method, path=path).time():
            response = await call_next(request)
        REQUESTS.labels(method=method, path=path, status=response.status_code).inc()
        return response

def expose():
    return generate_latest()
