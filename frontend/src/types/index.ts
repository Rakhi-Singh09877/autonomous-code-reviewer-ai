// Shared TypeScript declarations.

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type Dictionary<T> = Record<string, T>;
export type Severity = "info" | "low" | "medium" | "high" | "critical";
export type FocusArea = "security" | "performance" | "code_quality";
export type AnalysisStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
