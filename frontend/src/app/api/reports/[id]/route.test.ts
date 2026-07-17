import { NextRequest } from "next/server";
import { GET } from "./route";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

describe("GET /api/reports/[id] Route Handler", () => {
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

    const request = new NextRequest("http://localhost/api/reports/8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const context = { params: Promise.resolve({ id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4" }) };

    const response = await GET(request, context);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.message).toContain("BACKEND_API_URL is not configured");
  });

  it("should fail with 400 if id is not a valid UUID", async () => {
    const request = new NextRequest("http://localhost/api/reports/not-a-uuid");
    const context = { params: Promise.resolve({ id: "not-a-uuid" }) };

    const response = await GET(request, context);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("analysis_id must be a valid UUID");
  });

  it("should forward backend 400, 422, and 404 errors unchanged with Content-Type", async () => {
    const errorPayload = { detail: "Analysis report is not ready." };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(errorPayload), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      })
    );

    const request = new NextRequest("http://localhost/api/reports/8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const context = { params: Promise.resolve({ id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4" }) };

    const response = await GET(request, context);
    expect(response.status).toBe(400);
    expect(response.headers.get("content-type")).toContain("application/json");
    const body = await response.json();
    expect(body).toEqual(errorPayload);
  });

  it("should map backend 5xx errors to 502 Bad Gateway", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("Internal Server Error", {
        status: 500,
      })
    );

    const request = new NextRequest("http://localhost/api/reports/8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const context = { params: Promise.resolve({ id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4" }) };

    const response = await GET(request, context);
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.message).toContain("Bad Gateway");
  });

  it("should map fetch network failures to 503 Service Unavailable", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const request = new NextRequest("http://localhost/api/reports/8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const context = { params: Promise.resolve({ id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4" }) };

    const response = await GET(request, context);
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(body.message).toContain("Upstream report service is temporarily unavailable");
  });

  it("should return 502 if backend JSON response is invalid", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("{ invalid-json }", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const request = new NextRequest("http://localhost/api/reports/8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const context = { params: Promise.resolve({ id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4" }) };

    const response = await GET(request, context);
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.message).toContain("Invalid response format");
  });

  it("should return 502 if backend response fails validation against RepositoryReviewReportSchema", async () => {
    const invalidSchemaResponse = { id: "not-a-uuid", files_reviewed: 0 };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(invalidSchemaResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const request = new NextRequest("http://localhost/api/reports/8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    const context = { params: Promise.resolve({ id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4" }) };

    const response = await GET(request, context);
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.message).toContain("validation contract verification");
  });

  it("should successfully proxy and validate reports GET requests", async () => {
    const successResponse = {
      id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      repository_id: "723b7e7a-90da-4a5f-8d2a-0a7c9f8ab2e2",
      created_at: "2026-07-16T12:00:00Z",
      files_reviewed: 5,
      total_issues: 10,
      issues_by_severity: { HIGH: 2, MEDIUM: 8 },
      issues_by_category: { SECURITY: 2, BEST_PRACTICES: 8 },
      average_score: 88.5,
      file_results: [],
      token_usage: {
        prompt_tokens: 1500,
        completion_tokens: 800,
        total_tokens: 2300,
        estimated_cost_usd: 0.0076,
      },
    };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(successResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const request = new NextRequest("http://localhost/api/reports/8547f6b0-ed28-4d60-ade9-da892e2bd9d4", {
      headers: { "x-request-id": "test-req-id" },
    });
    const context = { params: Promise.resolve({ id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4" }) };

    const response = await GET(request, context);
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/json");

    const body = await response.json();
    expect(body).toEqual(successResponse);

    // Verify fetch arguments
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [targetUrl, options] = fetchMock.mock.calls[0];
    expect(targetUrl).toBe("http://mock-backend.com/api/v1/analysis/8547f6b0-ed28-4d60-ade9-da892e2bd9d4/report");
    expect(options.method).toBe("GET");
    expect(options.headers["X-Request-ID"]).toBe("test-req-id");
  });
});
