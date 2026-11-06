from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional

class AnalysisResponse(BaseModel):
    """ Response from endpoint /analyze """
    key_count: int
    types: Dict[str, str]
    nested_structure: Dict[str, Any]

class SchemaResponse(BaseModel):
    """ Response from endpoint /schema """
    model_config = ConfigDict(populate_by_name=True)
    # The internal field is named `json_schema` to avoid clashing with
    # BaseModel.schema(), but it maps to "schema" in the JSON via the alias.
    json_schema: Dict[str, Any] = Field(..., alias="schema")

class JsonExplanation(BaseModel):
    """ Structured, validated explanation produced by the AI. """
    summary: str = Field(..., description="Explicación legible en lenguaje natural")
    nesting_levels: int = Field(..., ge=0, description="Cantidad de niveles de anidación detectados")
    data_types: List[str] = Field(default_factory=list, description="Tipos de datos presentes en el JSON")
    important_fields: List[str] = Field(default_factory=list, description="Campos que parecen relevantes")

class ExplainResponse(BaseModel):
    """ Response from endpoint /explain (with AI). """
    explanation: JsonExplanation

class ErrorResponse(BaseModel):
    """ Standard error envelope produced by app.core.exceptions. """
    error: str
    status_code: int
    path: str
    details: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Only on 422: the validation errors"
    )
    message: Optional[str] = Field(
        default=None, description="Only on 500: a generic, user-facing message"
    )
