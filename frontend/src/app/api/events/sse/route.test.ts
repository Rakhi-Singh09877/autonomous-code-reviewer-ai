import { NextRequest } from "next/server";
import { GET } from "./route";
import { vi, describe, it, expect, beforeEach, afterEach, beforeAll } from "vitest";

describe("GET /api/events/sse BFF Proxy Handler", () => {
  const fetchMock = vi.fn();
  let originalEnv: string | undefined;

  beforeAll(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  beforeEach(() => {
    fetchMock.mockReset();
    originalEnv = process.env.BACKEND_API_URL;
    process.env.BACKEND_API_URL = "http://mock-backend.com";
  });

  afterEach(() => {
    process.env.BACKEND_API_URL = originalEnv;
  });

  it("should fail with 500 if BACKEND_API_URL is missing", async () => {
    delete process.env.BACKEND_API_URL;

    const request = new NextRequest("http://localhost/api/events/sse?analysis_id=8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const response = await GET(request);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.message).toContain("BACKEND_API_URL is not configured");
  });

  it("should fail with 400 if analysis_id query parameter is missing", async () => {
    const request = new NextRequest("http://localhost/api/events/sse");
    const response = await GET(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("analysis_id query parameter is required");
  });

  it("should fail with 400 if analysis_id is not a valid UUID", async () => {
    const request = new NextRequest("http://localhost/api/events/sse?analysis_id=invalid-uuid");
    const response = await GET(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("analysis_id must be a valid UUID");
  });

  it("should map fetch network failures to 503 Service Unavailable", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const request = new NextRequest("http://localhost/api/events/sse?analysis_id=8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const response = await GET(request);
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(body.message).toContain("Upstream events service is temporarily unavailable");
  });

  it("should map backend 500+ errors to 502 Bad Gateway", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("Internal Server Error", {
        status: 500,
      })
    );

    const request = new NextRequest("http://localhost/api/events/sse?analysis_id=8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const response = await GET(request);
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.message).toContain("Bad Gateway");
  });

  it("should map backend 400, 422, and 404 errors unchanged", async () => {
    const errorPayload = { detail: "Analysis not ready" };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(errorPayload), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      })
    );

    const request = new NextRequest("http://localhost/api/events/sse?analysis_id=8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const response = await GET(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body).toEqual(errorPayload);
  });

  it("should successfully proxy and stream events", async () => {
    const mockStream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("data: event1\n\n"));
        controller.close();
      },
    });

    fetchMock.mockResolvedValueOnce(
      new Response(mockStream, {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          "Connection": "keep-alive",
          "X-Accel-Buffering": "no",
        },
      })
    );

    const request = new NextRequest("http://localhost/api/events/sse?analysis_id=8547f6b0-ed28-4d60-ade9-da892e2bd9d4", {
      headers: { "x-request-id": "test-req-id" },
    });

    const response = await GET(request);
    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("text/event-stream");
    expect(response.headers.get("Cache-Control")).toContain("no-cache");
    expect(response.headers.get("Connection")).toBe("keep-alive");
    expect(response.headers.get("X-Accel-Buffering")).toBe("no");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [targetUrl, options] = fetchMock.mock.calls[0];
    expect(targetUrl).toBe("http://mock-backend.com/api/v1/events/sse?analysis_id=8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    expect(options.headers["X-Request-ID"]).toBe("test-req-id");

    const responseText = await response.text();
    expect(responseText).toBe("data: event1\n\n");
  });
});
