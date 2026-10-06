"""OpenTelemetry setup for Order Tracker (HW4, module 04).

One call site: ``setup_telemetry()`` at import time in ``app.main``.

Exports metrics, traces and structured logs:
- to the **console** when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is unset (Q2:
  inspect with ``docker compose logs app``),
- over **OTLP/HTTP** to the Collector when it is set (Q3 pipeline).

Signals and conventions:
- counter ``http.server.requests`` with attributes ``http.method``,
  ``http.route`` (the route TEMPLATE, e.g. /api/orders/{order_id}, so
  cardinality stays bounded) and ``http.status_code``;
- one SERVER span per request, same attributes, plus ``order.id`` when the
  path carries one;
- structured log records (JSON on console) carrying trace_id/span_id so a
  log line joins its trace, and business fields (order id, status) —
  never headers, tokens or payloads: nothing secret exists here, and the
  formatter would drop such fields by allowlist, not by accident.
"""

from __future__ import annotations

import atexit
import logging
import os

from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "order-tracker")

# Business fields allowed into log records (allowlist, not blocklist).
SAFE_LOG_FIELDS = ("order_id", "order_status", "priority", "http_status")


def setup_telemetry() -> tuple[trace.Tracer, metrics.Meter, logging.Logger]:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")  # e.g. http://collector:4318
    resource = Resource.create({"service.name": SERVICE_NAME})

    # ---- traces ----------------------------------------------------------
    if endpoint:
        span_exp = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
    else:
        # Write straight to a dup of fd 1: background exporter threads then
        # never touch sys.stdout, which pytest replaces/closes per test.
        console = os.fdopen(os.dup(1), "w", buffering=1)
        span_exp = ConsoleSpanExporter(out=console)
    tp = TracerProvider(resource=resource)
    tp.add_span_processor(BatchSpanProcessor(span_exp))
    trace.set_tracer_provider(tp)

    # ---- metrics ---------------------------------------------------------
    if endpoint:
        met_exp = OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics")
    else:
        met_exp = ConsoleMetricExporter(out=console)
    reader = PeriodicExportingMetricReader(met_exp, export_interval_millis=5000)
    mp = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(mp)

    # ---- logs ------------------------------------------------------------
    lp = LoggerProvider(resource=resource)
    if endpoint:
        log_exp = OTLPLogExporter(endpoint=f"{endpoint.rstrip('/')}/v1/logs")
    else:
        log_exp = ConsoleLogExporter(out=console)
    lp.add_log_record_processor(BatchLogRecordProcessor(log_exp))
    _logs.set_logger_provider(lp)

    logger = logging.getLogger("ordertracker")
    logger.setLevel(logging.INFO)
    logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=lp))
    logger.propagate = False  # keep uvicorn's stdout clean of duplicates

    tracer = trace.get_tracer(SERVICE_NAME)
    meter = metrics.get_meter(SERVICE_NAME)
    # Stop exporter threads at interpreter exit; otherwise the periodic
    # metric reader can flush onto a closed stdout during pytest teardown.
    atexit.register(mp.shutdown)
    atexit.register(tp.shutdown)
    atexit.register(lp.shutdown)
    return tracer, meter, logger


def request_counter(meter: metrics.Meter) -> metrics.Counter:
    return meter.create_counter(
        "http.server.requests",
        description="HTTP requests handled, by route template and status code",
        unit="1",
    )
