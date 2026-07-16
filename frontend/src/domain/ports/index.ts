import { Repository } from "../entities/repository.entity";
import { Analysis } from "../entities/analysis.entity";
import { RepositoryReviewReport } from "../entities/report.entity";
import { User } from "../entities/user.entity";

export interface IApiPort {
  submitAnalysis(payload: FormData): Promise<{ analysisId: string; status: string }>;
  getAnalysisStatus(analysisId: string): Promise<Analysis>;
  getAnalysisReport(analysisId: string): Promise<RepositoryReviewReport>;
}

export interface IAuthPort {
  login(credentials: unknown): Promise<User>;
  getCurrentUser(): Promise<User>;
  logout(): Promise<void>;
}

export interface SystemEvent {
  type: "ANALYSIS_PROGRESS" | "WORKER_STATUS_CHANGED" | "NEW_REPORT_ALERT";
  payload: any;
  timestamp: string;
}

export interface IEventPort {
  subscribe(channel: string, callback: (event: SystemEvent) => void): () => void;
  unsubscribe(channel: string): void;
}
