from sqlalchemy.orm import Session
from models.all_models import AIRegistry
import hashlib
import time
from typing import Dict, Any, Callable

class AIAuditService:
    @staticmethod
    def execute_and_audit(
        db: Session,
        entity_type: str,
        entity_id: str,
        operation: Callable,
        provider_name: str,
        model_name: str,
        prompt_version: str,
        pipeline_version: str,
        input_data: str,
    ) -> Any:
        """
        Executes an AI operation, measures latency, and records the telemetry/audit to the DB.
        """
        input_hash = hashlib.sha256(input_data.encode('utf-8')).hexdigest()
        
        start_time = time.time()
        
        try:
            # Operation should return (result, usage_dict)
            result, usage = operation()
            latency = time.time() - start_time
            
            # Record Success
            audit = AIRegistry(
                entity_type=entity_type,
                entity_id=entity_id,
                provider=provider_name,
                model_name=model_name,
                prompt_version=prompt_version,
                pipeline_version=pipeline_version,
                input_hash=input_hash,
                output_data=result.model_dump() if hasattr(result, 'model_dump') else {"result": "embedding_generated"},
                latency=latency,
                token_usage=usage
            )
            db.add(audit)
            db.commit()
            
            return result
            
        except Exception as e:
            latency = time.time() - start_time
            
            # Record Failure
            audit = AIRegistry(
                entity_type=entity_type,
                entity_id=entity_id,
                provider=provider_name,
                model_name=model_name,
                prompt_version=prompt_version,
                pipeline_version=pipeline_version,
                input_hash=input_hash,
                output_data={"error": str(e), "error_type": type(e).__name__},
                latency=latency
            )
            db.add(audit)
            db.commit()
            
            raise e
