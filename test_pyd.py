from pydantic import BaseModel
class ExtractedName(BaseModel):
    correct_name: str
obj = ExtractedName.model_validate_json('{"correct_name": "John"}')
print(obj.correct_name)
