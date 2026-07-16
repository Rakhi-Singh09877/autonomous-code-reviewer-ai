import axios, { AxiosError, AxiosInstance } from "axios";
import { IApiPort } from "../../domain/ports";
import { Analysis, RepositoryReviewReport } from "../../domain/entities";
import { AnalysisMapper, ReportMapper } from "./mappers";
import {
  AnalysisInitiateResponseSchema,
  AnalysisStatusResponseSchema,
  RepositoryReviewReportSchema,
} from "../../contracts";
import { env } from "../../config";
import {
  ValidationError,
  UnauthorizedError,
  ResourceNotFoundError,
  AppDomainError,
} from "../../domain/exceptions";

export class RestApiAdapter implements IApiPort {
  private readonly client: AxiosInstance;

  constructor(clientInstance?: AxiosInstance) {
    this.client = clientInstance || axios.create({
      baseURL: env.BFF_URL,
      timeout: 10000,
    });

    // Request interceptor to automatically inject X-Request-ID correlation headers
    this.client.interceptors.request.use((config) => {
      const requestId = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      config.headers = config.headers || {};
      config.headers["X-Request-ID"] = requestId;
      return config;
    });
  }

  public async submitAnalysis(payload: FormData): Promise<{ analysisId: string; status: string }> {
    try {
      const response = await this.client.post("/analyses", payload, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const parsed = AnalysisInitiateResponseSchema.parse(response.data);
      return {
        analysisId: parsed.analysis_id,
        status: parsed.status,
      };
    } catch (error) {
      throw this.handleError(error);
    }
  }

  public async getAnalysisStatus(analysisId: string): Promise<Analysis> {
    try {
      const response = await this.client.get(`/analyses/${analysisId}`);
      const parsed = AnalysisStatusResponseSchema.parse(response.data);
      return AnalysisMapper.toDomain(parsed);
    } catch (error) {
      throw this.handleError(error);
    }
  }

  public async getAnalysisReport(analysisId: string): Promise<RepositoryReviewReport> {
    try {
      const response = await this.client.get(`/reports/${analysisId}`);
      const parsed = RepositoryReviewReportSchema.parse(response.data);
      return ReportMapper.toReport(parsed);
    } catch (error) {
      throw this.handleError(error);
    }
  }

  private handleError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<{ message?: string; detail?: string; errors?: Record<string, string[]> }>;
      const status = axiosError.response?.status;
      const data = axiosError.response?.data;
      const message = data?.message || data?.detail || axiosError.message;

      switch (status) {
        case 400:
        case 422:
          const validationDetails = data?.errors || {};
          return new ValidationError(message, validationDetails);
        case 401:
        case 403:
          return new UnauthorizedError(message);
        case 404:
          return new ResourceNotFoundError(message);
        default:
          return new AppDomainError(message, `HTTP_ERROR_${status || "UNKNOWN"}`);
      }
    }

    if (error instanceof Error) {
      return error;
    }

    return new AppDomainError("An unexpected infrastructure error occurred", "UNKNOWN_ERROR");
  }
}
export default RestApiAdapter;
