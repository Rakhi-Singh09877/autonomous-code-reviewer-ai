import { http, HttpResponse } from "msw";

const MOCK_ANALYSIS_ID = "8547f6b0-ed28-4d60-ade9-da892e2bd9d4";

export const handlers = [
  // Health Check
  http.get("*/api/health", () => {
    return HttpResponse.json({ status: "healthy" });
  }),

  // Auth Login
  http.post("*/api/auth/login", async ({ request }) => {
    const body = (await request.json()) as { username?: string; password?: string };
    if (body.username === "error@domain.com") {
      return HttpResponse.json({ message: "Invalid credentials" }, { status: 401 });
    }
    if (body.username === "validation-error@domain.com") {
      return HttpResponse.json(
        { message: "Unprocessable Entity", errors: { password: ["Too short"] } },
        { status: 422 }
      );
    }
    return HttpResponse.json({
      access_token: "mock-jwt-token",
      token_type: "bearer",
    });
  }),

  // Auth Me (Current User)
  http.get("*/api/auth/me", () => {
    return HttpResponse.json({
      id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      email: "jd@domain.com",
      name: "John Doe",
      roles: ["admin"],
      permissions: ["write_reports"],
    });
  }),

  // Auth Logout
  http.post("*/api/auth/logout", () => {
    return HttpResponse.json({ message: "Success" });
  }),

  // Submit Analysis
  http.post("*/api/analyses", async ({ request }) => {
    // If request headers don't have correlation id, trigger error
    const requestId = request.headers.get("X-Request-ID");
    if (!requestId) {
      return HttpResponse.json({ message: "Correlation ID missing" }, { status: 400 });
    }
    return HttpResponse.json({
      analysis_id: MOCK_ANALYSIS_ID,
      status: "PENDING",
    });
  }),

  // Get Analysis Status
  http.get("*/api/analyses/:id", ({ params }) => {
    const { id } = params;
    if (id === "not-found") {
      return HttpResponse.json({ message: "Analysis not found" }, { status: 404 });
    }
    if (id === "server-crash") {
      return HttpResponse.json({ message: "Internal server error" }, { status: 500 });
    }
    return HttpResponse.json({
      analysis_id: id,
      status: "PROCESSING",
      progress_percentage: 60.0,
      current_file: "main.py",
      total_files: 10,
      errors: [],
    });
  }),

  // Get Review Report
  http.get("*/api/reports/:id", ({ params }) => {
    const { id } = params;
    return HttpResponse.json({
      id: id,
      repository_id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      created_at: "2026-07-16T10:00:00Z",
      files_reviewed: 1,
      total_issues: 0,
      issues_by_severity: {},
      issues_by_category: {},
      average_score: 95.0,
      file_results: [],
      token_usage: {
        prompt_tokens: 100,
        completion_tokens: 50,
        total_tokens: 150,
        estimated_cost_usd: 0.003,
      },
    });
  }),
];

export default handlers;
