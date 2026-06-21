from pydantic import BaseModel
from typing import Literal


class AskRequest(BaseModel):
    question: str
    language: Literal["en", "ar"] = "en"


class AskResponse(BaseModel):
    answer: str
    dax_query: str
    raw_data: str
    status: Literal["success", "error"]


class HealthResponse(BaseModel):
    status: str
    powerbi: str
    claude: str
