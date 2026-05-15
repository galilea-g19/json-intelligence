from pydantic import BaseModel, Field
from typing import Dict, Any

class JsonInput(BaseModel):
    data: Dict[str, Any] = Field(..., description="JSON Object to analyze")

    class Config:
        populate_by_name = True

        json_schema_extra = {
            "example": {
                "data": {
                    "name": "Name example",
                    "age": 30,
                    "skills": ["Python", "FastAPI"]
                }
            }
        }