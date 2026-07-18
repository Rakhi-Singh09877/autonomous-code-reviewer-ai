import axios, { AxiosInstance } from "axios";
import { env } from "@/config";
import {
  AnalysisInitiateResponseDTO,
  AnalysisStatusResponseDTO,
} from "@/contracts/analysis.contract";
import { RepositoryReviewReportDTO } from "@/contracts/reports.contract";

export interface CreateAnalysisRequest {
  gitUrl?: string;
  branch?: string;
  zipFile?: File | null;
  focusAreas?: string[];
  maxIssuesPerFile: number;
}

export class AnalysisService {
  private readonly client: AxiosInstance;

  constructor(clientInstance?: AxiosInstance) {
    this.client = clientInstance || axios.create({
      baseURL: env.BFF_URL,
      timeout: 15000,
    });

    this.client.interceptors.request.use((config) => {
      const requestId = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      config.headers = config.headers || {};
      config.headers["X-Request-ID"] = requestId;
      return config;
    });
  }

  public async createAnalysis(request: CreateAnalysisRequest): Promise<AnalysisInitiateResponseDTO> {
    const formData = new FormData();
    if (request.gitUrl) {
      formData.append("git_url", request.gitUrl);
    }
    if (request.branch) {
      formData.append("branch", request.branch);
    }
    if (request.zipFile) {
      formData.append("file", request.zipFile);
    }
    if (request.focusAreas && request.focusAreas.length > 0) {
      request.focusAreas.forEach((area) => {
        formData.append("focus_areas", area);
      });
    }
    formData.append("max_issues_per_file", String(request.maxIssuesPerFile));

    const response = await this.client.post<AnalysisInitiateResponseDTO>("/analyses", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  }

  public async getAnalysis(id: string): Promise<AnalysisStatusResponseDTO> {
    const response = await this.client.get<AnalysisStatusResponseDTO>(`/analyses/${id}`);
    return response.data;
  }

  public async getReport(id: string): Promise<RepositoryReviewReportDTO> {
    const response = await this.client.get<RepositoryReviewReportDTO>(`/reports/${id}`);
    return response.data;
  }
}

export const analysisService = new AnalysisService();
