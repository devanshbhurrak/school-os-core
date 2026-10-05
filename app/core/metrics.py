"""Prometheus metrics setup for school-os-api.

Instruments the FastAPI app with request/latency histograms via
`prometheus-fastapi-instrumentator` and exposes custom counters for
application-level events (e.g. auth failures).
"""
from __future__ import annotations

from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

# ---------------------------------------------------------------------------
# Custom application counters
# ---------------------------------------------------------------------------

auth_failures_total = Counter(
    "auth_failures_total",
    "Total authentication failures",
    ["reason"],
)


# ---------------------------------------------------------------------------
# Instrumentator setup
# ---------------------------------------------------------------------------


def setup_metrics(app) -> None:  # noqa: ANN001
    """Attach Prometheus instrumentation to *app* and expose /metrics."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/health", "/health/ready", "/metrics"],
    )
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
