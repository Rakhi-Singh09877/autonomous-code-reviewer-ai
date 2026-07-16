export const gitUrlRegex = /^(https:\/\/|git@)([a-zA-Z0-9.-]+)([:/][a-zA-Z0-9_.-]+)+(\.git)?$/;

export function validateGitUrl(url: string): boolean {
  return gitUrlRegex.test(url);
}

export function isSafePath(filePath: string): boolean {
  // Security validation: verify path does not contain relative traversal structures like '..'
  const segments = filePath.split(/[/\\]/);
  return !segments.includes("..");
}

export function validateZipSize(sizeInBytes: number, maxMb: number): boolean {
  const sizeInMb = sizeInBytes / (1024 * 1024);
  return sizeInMb <= maxMb;
}
