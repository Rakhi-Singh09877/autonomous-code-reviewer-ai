import { NextRequest } from "next/server";
import { POST } from "./route";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

describe("POST /api/analyses Route Handler", () => {
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

    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.message).toContain("BACKEND_API_URL is not configured");
  });

  it("should fail with 400 if neither git_url nor file are provided", async () => {
    const formData = new FormData();
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("Either git_url or file upload must be provided");
  });

  it("should fail with 400 if both git_url and file are provided", async () => {
    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    formData.append("file", new File(["test"], "repo.zip", { type: "application/zip" }));
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("Provide either git_url or file upload, not both");
  });

  it("should fail with 400 if git_url is invalid", async () => {
    const formData = new FormData();
    formData.append("git_url", "not-a-valid-url");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("git_url must be a valid URL");
  });

  it("should fail with 400 if file does not have .zip extension", async () => {
    const formData = new FormData();
    formData.append("file", new File(["test"], "repo.txt", { type: "text/plain" }));
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("Only ZIP archives are supported");
  });

  it("should fail with 400 if branch is empty after trimming", async () => {
    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    formData.append("branch", "   ");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("branch cannot be empty");
  });

  it("should fail with 400 if max_issues_per_file is not a positive integer", async () => {
    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    formData.append("max_issues_per_file", "-1");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.message).toContain("max_issues_per_file must be a positive integer");
  });

  it("should forward backend 400, 422, and 404 errors unchanged with Content-Type", async () => {
    const errorPayload = { detail: "Analysis error context" };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(errorPayload), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      })
    );

    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(422);
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

    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.message).toContain("Bad Gateway");
  });

  it("should map fetch network failures to 503 Service Unavailable", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(body.message).toContain("Upstream analysis service is temporarily unavailable");
  });

  it("should return 502 if backend JSON response is invalid", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("{ invalid-json }", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.message).toContain("Invalid response format");
  });

  it("should return 502 if backend response fails validation against AnalysisInitiateResponseSchema", async () => {
    const invalidSchemaResponse = { analysis_id: "not-a-uuid", status: "PENDING" };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(invalidSchemaResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.message).toContain("validation contract verification");
  });

  it("should successfully proxy and validate analyses POST requests", async () => {
    const successResponse = {
      analysis_id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      status: "PENDING",
    };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(successResponse), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      })
    );

    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    formData.append("branch", "main");
    formData.append("focus_areas", "security,performance");
    formData.append("max_issues_per_file", "10");

    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
      headers: { "x-request-id": "test-req-id" },
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(202);
    expect(response.headers.get("content-type")).toContain("application/json");

    const body = await response.json();
    expect(body).toEqual(successResponse);

    // Verify fetch arguments
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [targetUrl, options] = fetchMock.mock.calls[0];
    expect(targetUrl).toBe("http://mock-backend.com/api/v1/analyze");
    expect(options.method).toBe("POST");
    expect(options.headers["X-Request-ID"]).toBe("test-req-id");
    expect(options.body).toBeInstanceOf(FormData);

    const forwardedForm = options.body as FormData;
    expect(forwardedForm.get("git_url")).toBe("https://github.com/user/repo");
    expect(forwardedForm.get("branch")).toBe("main");
    expect(forwardedForm.get("focus_areas")).toBe("security,performance");
    expect(forwardedForm.get("max_issues_per_file")).toBe("10");
  });

  it("should successfully support file uploads", async () => {
    const successResponse = {
      analysis_id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      status: "PENDING",
    };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(successResponse), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      })
    );

    const file = new File(["zip-content"], "archive.zip", { type: "application/zip" });
    const formData = new FormData();
    formData.append("file", file);

    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    const response = await POST(request);
    expect(response.status).toBe(202);

    const body = await response.json();
    expect(body).toEqual(successResponse);

    const forwardedForm = fetchMock.mock.calls[0][1].body as FormData;
    expect(forwardedForm.get("file")).toBeInstanceOf(File);
    expect((forwardedForm.get("file") as File).name).toBe("archive.zip");
  });

  it("should support repeated focus_areas fields and merge them", async () => {
    const successResponse = {
      analysis_id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      status: "PENDING",
    };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(successResponse), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      })
    );

    const formData = new FormData();
    formData.append("git_url", "https://github.com/user/repo");
    formData.append("focus_areas", "security");
    formData.append("focus_areas", "performance,  quality");

    const request = new NextRequest("http://localhost/api/analyses", {
      method: "POST",
    });
    request.formData = async () => formData;

    await POST(request);

    const forwardedForm = fetchMock.mock.calls[0][1].body as FormData;
    expect(forwardedForm.get("focus_areas")).toBe("security,performance,quality");
  });
});
