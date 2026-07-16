export class AppDomainError extends Error {
  constructor(message: string, public readonly code: string) {
    super(message);
    this.name = "AppDomainError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class ValidationError extends AppDomainError {
  constructor(message: string, public readonly details: Record<string, string[]> = {}) {
    super(message, "VALIDATION_ERROR");
    this.name = "ValidationError";
  }
}

export class DomainRuleViolationError extends AppDomainError {
  constructor(message: string) {
    super(message, "DOMAIN_RULE_VIOLATION");
    this.name = "DomainRuleViolationError";
  }
}

export class UnauthorizedError extends AppDomainError {
  constructor(message: string = "Access denied due to invalid credentials.") {
    super(message, "UNAUTHORIZED");
    this.name = "UnauthorizedError";
  }
}

export class ResourceNotFoundError extends AppDomainError {
  constructor(message: string) {
    super(message, "RESOURCE_NOT_FOUND");
    this.name = "ResourceNotFoundError";
  }
}
