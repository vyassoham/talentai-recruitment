import os
import requests
import time

def run_acceptance_test():
    # This script simulates uploading 50 CVs to the API
    # It assumes the FastAPI server is running at http://localhost:8000
    
    BASE_URL = "http://localhost:8000/api/v1"
    
    # Check if API is up
    try:
        requests.get(f"{BASE_URL}/health")
    except requests.ConnectionError:
        print("API is not running. Start it with `uvicorn main:app --reload` first.")
        return

    print("Starting 50 CV Ingestion Acceptance Test...")
    
    # Create a dummy PDF
    dummy_pdf_path = "dummy_cv.pdf"
    with open(dummy_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        
    job_ids = []
    
    # Simulate 50 uploads
    for i in range(50):
        with open(dummy_pdf_path, "rb") as f:
            # We add a slight variation to the filename/content to avoid duplicate hash blocking for all 50
            f_data = f.read() + f" variation {i}".encode()
            
        files = {"file": (f"cv_{i}.pdf", f_data, "application/pdf")}
        resp = requests.post(f"{BASE_URL}/candidates/upload", files=files)
        
        if resp.status_code == 200:
            job_ids.append(resp.json()["job_id"])
        else:
            print(f"Failed to upload CV {i}: {resp.text}")
            
    print(f"Successfully queued {len(job_ids)} jobs.")
    
    # Poll until done
    pending = True
    while pending:
        time.sleep(2)
        pending = False
        completed = 0
        failed = 0
        for jid in job_ids:
            resp = requests.get(f"{BASE_URL}/jobs/{jid}")
            if resp.status_code == 200:
                data = resp.json()
                if data["status"] in ["QUEUED", "IN_PROGRESS"]:
                    pending = True
                elif data["status"] == "COMPLETED":
                    completed += 1
                elif data["status"] == "FAILED":
                    failed += 1
                    print(f"Job {jid} failed at stage {data['stage']}: {data['error']}")
        
        print(f"Status: {completed} Completed, {failed} Failed, {len(job_ids) - completed - failed} Pending...")

    print("Acceptance Test Finished.")
    if os.path.exists(dummy_pdf_path):
        os.remove(dummy_pdf_path)

if __name__ == "__main__":
    run_acceptance_test()
