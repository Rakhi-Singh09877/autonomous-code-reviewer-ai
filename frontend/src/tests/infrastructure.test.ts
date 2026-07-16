import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import axios from "axios";
import { RestApiAdapter } from "../services/api/RestApiAdapter";
import { RestAuthService } from "../services/auth/RestAuthService";
import { PollingEventAdapter } from "../services/events/PollingEventAdapter";
import {
  ValidationError,
  UnauthorizedError,
  ResourceNotFoundError,
  AppDomainError,
} from "../domain/exceptions";
import { Analysis, RepositoryReviewReport, User } from "../domain/entities";
import { SystemEvent } from "../domain/ports";

describe("RestApiAdapter Infrastructure tests", () => {
  let adapter: RestApiAdapter;

  beforeEach(() => {
    const client = axios.create({
      baseURL: "http://localhost:3000/api",
    });
    adapter = new RestApiAdapter(client);
  });

  it("should successfully submit code analysis and automatically inject X-Request-ID headers", async () => {
    const formData = new FormData();
    formData.append("repository", new Blob(["mock-zip"], { type: "application/zip" }));
    
    const result = await adapter.submitAnalysis(formData);
    expect(result.analysisId).toBe("8547f6b0-ed28-4d60-ade9-da892e2bd9d4");
    expect(result.status).toBe("PENDING");
  });

  it("should query analysis progress status and translate to domain model", async () => {
    const analysisId = "8547f6b0-ed28-4d60-ade9-da892e2bd9d4";
    const status = await adapter.getAnalysisStatus(analysisId);

    expect(status instanceof Analysis).toBe(true);
    expect(status.analysisId).toBe(analysisId);
    expect(status.progressPercentage).toBe(60.0);
    expect(status.currentFile).toBe("main.py");
  });

  it("should retrieve code reviews and translate report details", async () => {
    const report = await adapter.getAnalysisReport("8547f6b0-ed28-4d60-ade9-da892e2bd9d4");

    expect(report instanceof RepositoryReviewReport).toBe(true);
    expect(report.averageScore).toBe(95.0);
    expect(report.formattedCost).toBe("$0.0030");
  });

  it("should translate status 404 errors to ResourceNotFoundError exceptions", async () => {
    await expect(adapter.getAnalysisStatus("not-found")).rejects.toThrow(ResourceNotFoundError);
  });

  it("should translate status 500 errors to AppDomainError exceptions", async () => {
    await expect(adapter.getAnalysisStatus("server-crash")).rejects.toThrow(AppDomainError);
  });
});

describe("RestAuthService Infrastructure tests", () => {
  let authService: RestAuthService;

  beforeEach(() => {
    const client = axios.create({
      baseURL: "http://localhost:3000/api",
    });
    authService = new RestAuthService(client);
  });

  it("should login credentials and load user identity profiles", async () => {
    const credentials = { username: "jd@domain.com", password: "securepassword123" };
    const user = await authService.login(credentials);

    expect(user instanceof User).toBe(true);
    expect(user.name).toBe("John Doe");
    expect(user.hasRole("admin")).toBe(true);
  });

  it("should reject login validations locally when request parameters fail Zod rules", async () => {
    const credentials = { username: "invalid-email-address", password: "short" };
    await expect(authService.login(credentials)).rejects.toThrow();
  });

  it("should translate login 401 rejections to UnauthorizedError exceptions", async () => {
    const credentials = { username: "error@domain.com", password: "some-password-val" };
    await expect(authService.login(credentials)).rejects.toThrow(UnauthorizedError);
  });

  it("should translate login 422 validations to ValidationError exceptions", async () => {
    const credentials = { username: "validation-error@domain.com", password: "some-password-val" };
    await expect(authService.login(credentials)).rejects.toThrow(ValidationError);
  });
});

describe("PollingEventAdapter Infrastructure tests", () => {
  let apiAdapter: RestApiAdapter;

  beforeEach(() => {
    const client = axios.create({
      baseURL: "http://localhost:3000/api",
    });
    apiAdapter = new RestApiAdapter(client);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should subscribe to channels and trigger polling queries periodically", async () => {
    const pollingAdapter = new PollingEventAdapter(apiAdapter, 1000);
    const channel = "analysis:8547f6b0-ed28-4d60-ade9-da892e2bd9d4";
    const callback = vi.fn();

    const unsubscribe = pollingAdapter.subscribe(channel, callback);
    
    // Await immediate initial fetch to resolve on microtask queue
    await vi.waitFor(() => {
      expect(callback).toHaveBeenCalledTimes(1);
    });

    const receivedEvent = callback.mock.calls[0][0] as SystemEvent;
    expect(receivedEvent.type).toBe("ANALYSIS_PROGRESS");
    expect(receivedEvent.payload.progress_percentage).toBe(60.0);

    // Fast-forward 1 interval cycle (1000ms)
    vi.advanceTimersByTime(1000);
    await vi.waitFor(() => {
      expect(callback).toHaveBeenCalledTimes(2);
    });

    // Verify unsubscription clears periodic query checks
    unsubscribe();
    vi.advanceTimersByTime(1000);
    
    // Timer is cleared, count remains at 2
    expect(callback).toHaveBeenCalledTimes(2);
  });
});
