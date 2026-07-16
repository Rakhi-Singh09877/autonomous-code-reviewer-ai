export type RepositorySourceType = "GIT" | "ZIP";

export class Repository {
  constructor(
    public readonly id: string,
    public readonly localPath: string,
    public readonly sourceType: RepositorySourceType,
    public readonly fileCount: number,
    public readonly totalSizeBytes: number,
    public readonly gitUrl?: string,
    public readonly branch?: string
  ) {}

  public get sizeInMb(): number {
    return Number((this.totalSizeBytes / (1024 * 1024)).toFixed(2));
  }
}
