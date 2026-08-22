"""Pydantic models for ZFP Advisor API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    language: Literal["en", "ar"] = "en"


class AskResponse(BaseModel):
    answer: str
    sql_query: str
    status: Literal["success", "error"]


class HealthResponse(BaseModel):
    status: str
    database: str
    claude: str
    version: str = "1.1.0"
