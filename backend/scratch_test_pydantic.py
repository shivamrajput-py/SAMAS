from pydantic import BaseModel, Field, model_validator
from typing import Any
from enum import Enum

class SkillCategory(str, Enum):
    FRAMEWORK = "framework"
    OTHER = "other"

class ExtractedSkillEntry(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: SkillCategory
    parent_domain: str = Field(min_length=1, max_length=100)

    @model_validator(mode="before")
    @classmethod
    def coerce_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cat = data.get("category")
            if isinstance(cat, str):
                try:
                    SkillCategory(cat)
                except ValueError:
                    data["category"] = "other"
            elif not cat:
                data["category"] = "other"
                
            pd = data.get("parent_domain")
            if not pd or not isinstance(pd, str):
                data["parent_domain"] = "Unknown"
                
            name = data.get("name")
            if not name or not isinstance(name, str):
                data["name"] = "Unknown Skill"
        return data

data = {"name": "Test", "category": "framework", "parent_domain": None}
try:
    print(ExtractedSkillEntry.model_validate(data))
except Exception as e:
    print(e)
