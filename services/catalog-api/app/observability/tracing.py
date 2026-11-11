from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def init_tracer(service_name: str, endpoint: str, enabled: bool = True) -> trace.Tracer:
    # Provider is always installed so traceparent propagates and logs carry trace_ids;
    # the OTLP exporter is attached only when a collector endpoint is enabled.
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if enabled:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor: SpanProcessor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def inject_trace_context(carrier: dict[str, str]) -> None:
    TraceContextTextMapPropagator().inject(carrier)


def extract_trace_context(carrier: dict[str, str]):
    return TraceContextTextMapPropagator().extract(carrier)
