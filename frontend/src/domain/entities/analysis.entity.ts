export type AnalysisStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export class Analysis {
  constructor(
    public readonly analysisId: string,
    public readonly status: AnalysisStatus,
    public readonly progressPercentage: number,
    public readonly currentFile: string | null,
    public readonly totalFiles: number,
    public readonly errors: string[]
  ) {}

  public get isFinished(): boolean {
    return this.status === "COMPLETED" || this.status === "FAILED";
  }

  public get isFailed(): boolean {
    return this.status === "FAILED";
  }

  public get isProcessing(): boolean {
    return this.status === "PROCESSING" || this.status === "PENDING";
  }
}
