/**
 * src/instrumentation.ts
 *
 * Next.js 15 startup hooks entry point.
 * Initializes OpenTelemetry NodeSDK when running on the Node.js server context.
 * Dynamic imports are used to prevent OTel libraries from bleeding into browser/Edge bundles.
 */

let shutdownHandlersRegistered = false;

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const tracesEndpoint = process.env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT;
    const genericEndpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;

    // Do not initialize the SDK if no OTLP trace exporter endpoint configuration is provided
    if (!tracesEndpoint && !genericEndpoint) {
      console.info("OpenTelemetry trace exporter endpoints (OTEL_EXPORTER_OTLP_TRACES_ENDPOINT / OTEL_EXPORTER_OTLP_ENDPOINT) are not configured. SDK initialization bypassed.");
      return;
    }

    try {
      const { NodeSDK } = await import("@opentelemetry/sdk-node");
      const { OTLPTraceExporter } = await import("@opentelemetry/exporter-trace-otlp-http");
      const { defaultResource, resourceFromAttributes } = await import("@opentelemetry/resources");
      const {
        SEMRESATTRS_SERVICE_NAME,
        SEMRESATTRS_SERVICE_VERSION,
        SEMRESATTRS_DEPLOYMENT_ENVIRONMENT,
      } = await import("@opentelemetry/semantic-conventions");

      // Compute exact OTLP target URL based on preference
      const endpoint = tracesEndpoint || `${genericEndpoint}/v1/traces`;

      const traceExporter = new OTLPTraceExporter({
        url: endpoint,
      });

      // Construct resource descriptors using modern v2.x.x non-constructible type/interface wrappers
      const resource = defaultResource().merge(
        resourceFromAttributes({
          [SEMRESATTRS_SERVICE_NAME]: process.env.OTEL_SERVICE_NAME || "autonomous-code-reviewer-frontend",
          [SEMRESATTRS_SERVICE_VERSION]: process.env.OTEL_SERVICE_VERSION || "0.1.0",
          [SEMRESATTRS_DEPLOYMENT_ENVIRONMENT]: process.env.NODE_ENV || "development",
        })
      );

      const sdk = new NodeSDK({
        resource,
        traceExporter,
      });

      // Call start synchronously as per v0.220.x API contracts
      sdk.start();
      console.info(`OpenTelemetry SDK started successfully. Exporting traces to: ${endpoint}`);

      // Graceful shutdown triggers — register handlers only once to prevent memory leaks
      if (!shutdownHandlersRegistered) {
        const handleShutdown = (signal: string) => {
          console.info(`Received ${signal}, shutting down OpenTelemetry SDK...`);
          sdk.shutdown()
            .then(() => console.info("OpenTelemetry SDK shutdown completed successfully."))
            .catch((err) => console.error("Error encountered during OpenTelemetry SDK shutdown:", err));
        };

        process.on("SIGTERM", () => handleShutdown("SIGTERM"));
        process.on("SIGINT", () => handleShutdown("SIGINT"));
        shutdownHandlersRegistered = true;
      }

    } catch (error) {
      console.error("OpenTelemetry SDK initialization failed:", error);
    }
  }
}
