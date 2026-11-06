from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any

class JsonInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": {
                    "name": "Name example",
                    "age": 30,
                    "skills": ["Python", "FastAPI"]
                }
            }
        }
    )

    data: Dict[str, Any] = Field(..., description="JSON Object to analyze")
