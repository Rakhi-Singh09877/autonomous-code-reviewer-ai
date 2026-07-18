import { describe, it, expect } from "vitest";
import { analysisService } from "../services/api/analysisService";

describe("AnalysisService tests", () => {
  it("should successfully create analysis via BFF", async () => {
    const request = {
      gitUrl: "https://github.com/mock/repo",
      branch: "main",
      focusAreas: ["security", "performance"],
      maxIssuesPerFile: 15,
    };

    const response = await analysisService.createAnalysis(request);
    expect(response.analysis_id).toBe("8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    expect(response.status).toBe("PENDING");
  });

  it("should successfully retrieve analysis status", async () => {
    const response = await analysisService.getAnalysis("8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    expect(response.analysis_id).toBe("8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    expect(response.status).toBe("PROCESSING");
    expect(response.progress_percentage).toBe(60.0);
    expect(response.current_file).toBe("main.py");
  });

  it("should successfully retrieve analysis report", async () => {
    const response = await analysisService.getReport("8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    expect(response.id).toBe("8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    expect(response.average_score).toBe(95.0);
    expect(response.token_usage.total_tokens).toBe(150);
  });
});
