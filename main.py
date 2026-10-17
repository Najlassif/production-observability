
import time
import uuid
import json
import logging
import os
import threading
from collections import deque

from fastapi import FastAPI, Request, Query
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

EMAIL = "22f3000259@ds.study.iitm.ac.in"

app = FastAPI()

START_TIME = time.monotonic()

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests"
)

LOGS = deque(maxlen=10000)
LOCK = threading.Lock()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("observability")


@app.middleware("http")
async def track_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    REQUEST_COUNTER.inc()

    try:
        response = await call_next(request)
    except Exception:
        record = {
            "level": "ERROR",
            "ts": time.time(),
            "path": request.url.path,
            "request_id": request_id
        }
        with LOCK:
            LOGS.append(record)
        logger.error(json.dumps(record))
        raise

    record = {
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id
    }

    with LOCK:
        LOGS.append(record)

    logger.info(json.dumps(record))
    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/work")
def work(n: int = Query(default=1, ge=0)):
    for _ in range(n):
        pass

    return {
        "email": EMAIL,
        "done": n
    }


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_s": float(time.monotonic() - START_TIME)
    }


@app.get("/logs/tail")
def logs_tail(limit: int = Query(default=10, ge=0)):
    with LOCK:
        if limit == 0:
            return []
        return list(LOGS)[-limit:]


@app.get("/")
def home():
    return {
        "message": "Observability API running",
        "email": EMAIL
    }
