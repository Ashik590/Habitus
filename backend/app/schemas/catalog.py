from pydantic import BaseModel, ConfigDict


class LanguagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    bengali_name: str


