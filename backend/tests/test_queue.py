import pytest
import time
from unittest.mock import patch, MagicMock
from core.queue import LocalThreadQueue

def dummy_task(job_id: str, **kwargs):
    time.sleep(0.05)
    if kwargs.get("fail"):
        raise ValueError("Simulated Failure")
    return {"status": "ok", "processed": True}

def wait_for_status(queue, job_id, target_statuses, timeout=5.0):
    start = time.time()
    while time.time() - start < timeout:
        status = queue.get_status(job_id)
        if status and status["status"] in target_statuses:
            return status
        time.sleep(0.1)
    return queue.get_status(job_id)

def test_local_thread_queue():
    queue = LocalThreadQueue()
    
    # Enqueue a successful job
    job_id = queue.enqueue(
        job_type="TEST_JOB",
        payload={"data": "test"},
        task_func=dummy_task
    )
    
    # Check initial status
    status = queue.get_status(job_id)
    assert status is not None
    
    # Wait for completion
    status = wait_for_status(queue, job_id, ["COMPLETED"])
    assert status["status"] == "COMPLETED"
    assert status["result"] == {"status": "ok", "processed": True}
    
    # Enqueue a failing job
    job_id_fail = queue.enqueue(
        job_type="TEST_JOB",
        payload={"data": "test"},
        task_func=dummy_task,
        fail=True
    )
    status_fail = wait_for_status(queue, job_id_fail, ["FAILED"])
    assert status_fail["status"] == "FAILED"
    assert "Simulated Failure" in status_fail["error"]

def test_job_cancellation():
    queue = LocalThreadQueue()
    
    def long_task(job_id: str, **kwargs):
        time.sleep(2)
        return "done"
        
    job_id = queue.enqueue(
        job_type="LONG_JOB",
        payload={},
        task_func=long_task
    )
    
    # Cancel immediately
    success = queue.cancel(job_id)
    assert success is True
    
    status = queue.get_status(job_id)
    assert status["status"] == "CANCELLED"
    
    # Wait to ensure it remains cancelled
    time.sleep(0.5)
    status_after = queue.get_status(job_id)
    assert status_after["status"] == "CANCELLED"
