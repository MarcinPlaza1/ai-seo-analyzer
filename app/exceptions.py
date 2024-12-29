class AuditException(Exception):
    """Base exception for audit related errors"""
    pass

class AuditNotFound(AuditException):
    """Raised when audit is not found"""
    pass

class CrawlerError(AuditException):
    """Raised when crawler encounters an error"""
    pass

class ContentNotFoundError(AuditException):
    """Raised when required content is not found"""
    pass

class SerpAnalyError(AuditException):
    """Raised when SERP analysis fails"""
    pass

class AuditDataNotFound(AuditException):
    """Raised when audit data is not found or is invalid"""
    pass

class SerpAPIError(AuditException):
    """Raised when SERP API request fails"""
    pass 