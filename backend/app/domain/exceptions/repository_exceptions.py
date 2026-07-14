class RepositoryLoaderException(Exception):
    """Base exception for all repository loading failures."""
    pass

class InvalidRepositoryURLException(RepositoryLoaderException):
    """Exception raised when the provided Git URL is invalid or malformed."""
    pass

class SecurityException(RepositoryLoaderException):
    """Exception raised when a security violation (e.g. traversal attempt) is detected."""
    pass

class ZipSlipException(SecurityException):
    """Exception raised specifically when a Zip Slip/directory traversal attempt is detected inside a ZIP file."""
    pass

class CloneTimeoutException(RepositoryLoaderException):
    """Exception raised when cloning the Git repository times out."""
    pass
