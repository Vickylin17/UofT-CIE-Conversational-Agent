class ConfigurationError(Exception):
    """Raised when runtime configuration is invalid or incomplete."""


class ScrapingError(Exception):
    """Raised when the crawler cannot collect source content."""


class RetrievalError(Exception):
    """Raised when the vector store cannot fulfill a retrieval request."""


class ToolExecutionError(Exception):
    """Raised when an action tool fails."""
