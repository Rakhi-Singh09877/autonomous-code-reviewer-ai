class AgentException(Exception):
    """Base exception for all agent and LLM-related failures."""
    pass

class LLMException(AgentException):
    """Base exception for LLM operations failures."""
    pass

class LLMConnectionException(LLMException):
    """Exception raised when connection to LLM API fails or times out."""
    pass

class LLMRateLimitException(LLMException):
    """Exception raised when LLM API rate limits (HTTP 429) are encountered."""
    pass

class LLMInvalidAPIKeyException(LLMException):
    """Exception raised when API authentication fails."""
    pass

class LLMResponseParsingException(LLMException):
    """Exception raised when output from LLM cannot be parsed or validated."""
    pass

class ReviewValidationException(AgentException):
    """Exception raised when review results fail logical validation checks."""
    pass
