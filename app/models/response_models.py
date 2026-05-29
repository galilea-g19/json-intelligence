from pydantic import BaseModel
from typing import Dict, Any, Optional

class AnalysisResponse(BaseModel):
    """ Response from endpoint /analyze """
    key_count: int
    types: Dict[str, str]
    nested_structure: Dict[str, Any]

class SchemaResponse(BaseModel):
    """ Response from endpoint / schema """
    schema: Dict[str, Any]

class ExplainResponse(BaseModel):
    """ Response from endpoint /explain (With AI)"""
    explanation: str

class ErrorResponse(BaseModel):
    """ Standar response for errors """
    error: str
    details: Optional[str] = None

class ExplainResponse(BaseModel):
    explanation: str