from pydantic import BaseModel
from typing import Dict, Any, Optional

class AnalysisResponse(BaseModel):
    key_count: int
    types: Dict[str, str]
    nested_structure: Dict[str, Any]

class SchemaResponse():
    schema: Dict[str, Any]

class ExplainResponse(BaseModel):
    explanation: str

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None