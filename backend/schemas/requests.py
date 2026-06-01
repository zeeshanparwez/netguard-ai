"""
Pydantic request/response schemas.
Kept separate from the API layer so they can be imported by services without
creating a circular dependency on FastAPI itself.
"""

from typing import List

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str       # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class MatrixRequest(BaseModel):
    states: List[str]
    matrix: List[List[float]]
