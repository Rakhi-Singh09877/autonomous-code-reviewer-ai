export class TokenUsage {
  constructor(
    public readonly promptTokens: number,
    public readonly completionTokens: number,
    public readonly totalTokens: number,
    public readonly estimatedCostUsd: number
  ) {
    // Value objects validation in constructor
    if (promptTokens < 0 || completionTokens < 0 || totalTokens < 0 || estimatedCostUsd < 0) {
      throw new Error("Token metrics cannot be negative values.");
    }
    Object.freeze(this); // Enforces immutability
  }

  public plus(other: TokenUsage): TokenUsage {
    return new TokenUsage(
      this.promptTokens + other.promptTokens,
      this.completionTokens + other.completionTokens,
      this.totalTokens + other.totalTokens,
      this.estimatedCostUsd + other.estimatedCostUsd
    );
  }
}
