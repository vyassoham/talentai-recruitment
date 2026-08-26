import time
import os
from scripts.fast_ingest import fast_ingest_all
import logging

logging.basicConfig(level=logging.INFO)

def watch():
    folder = r"D:\recruitment_platform\gdrive_resumes_batch2"
    logging.info(f"Starting continuous watcher on {folder}")
    while True:
        try:
            fast_ingest_all(folder)
        except Exception as e:
            logging.error(f"Error in batch: {e}")
        time.sleep(60)

if __name__ == "__main__":
    watch()
