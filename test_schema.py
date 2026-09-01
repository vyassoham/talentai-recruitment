from services.ai.provider import get_ai_provider
from services.documents.schemas import StructuredCandidate
import json

schema_json = StructuredCandidate.model_json_schema()
print('Schema fields:', list(schema_json['properties'].keys()))
