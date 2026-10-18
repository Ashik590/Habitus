from pydantic import BaseModel, ConfigDict


class LanguagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    bengali_name: str


class DimensionPublic(BaseModel):
    code: str
    name: str
    bengali_name: str
    display_order: int


class ModulePublic(BaseModel):
    code: str
    name: str
    bengali_name: str
    dimensions: list[DimensionPublic]
