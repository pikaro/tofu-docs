"""Models for the writer module."""

from pydantic import BaseModel


class WriterResult(BaseModel):
    """Result of the write operation."""

    changed: bool
    content: str
    original_content: str | None
