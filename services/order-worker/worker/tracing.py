from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def init_worker_tracer(service_name: str, endpoint: str, enabled: bool = True) -> trace.Tracer:
    # Provider is always installed so worker spans exist and carry the API trace_id
    # even before the Tempo collector lands; exporter attached only when enabled.
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if enabled:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor: SpanProcessor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def extract_trace_context(carrier: dict[str, str]) -> Context:
    return TraceContextTextMapPropagator().extract(carrier)
