import re
import os
import requests
import concurrent.futures

log_path = r'C:\Users\dell\.gemini\antigravity\brain\db9911ae-e671-413c-95f9-5d67374ba351\.system_generated\tasks\task-2837.log'
out_dir = r'D:\recruitment_platform\gdrive_resumes_batch2'
os.makedirs(out_dir, exist_ok=True)

files = []
with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        match = re.search(r'Processing file ([a-zA-Z0-9_-]{33}) (.*\.pdf)', line, re.IGNORECASE)
        if match:
            files.append((match.group(1), match.group(2).strip()))

print(f'Found {len(files)} PDFs in logs.')

def download_file(file_info):
    fid, fname = file_info
    # Clean fname
    fname = "".join([c for c in fname if c.isalpha() or c.isdigit() or c in ' ._-']).rstrip()
    if not fname.lower().endswith('.pdf'):
        fname += '.pdf'
    
    out_path = os.path.join(out_dir, fname)
    if os.path.exists(out_path):
        return True
        
    url = f'https://drive.google.com/uc?id={fid}&export=download'
    try:
        session = requests.Session()
        res = session.get(url, stream=True, timeout=15)
        
        # Check for Google Drive virus scan warning
        if 'confirm=' in res.text:
            match = re.search(r'confirm=([0-9A-Za-z_]+)', res.text)
            if match:
                res = session.get(url + f'&confirm={match.group(1)}', stream=True)
                
        if res.status_code == 200 and 'text/html' not in res.headers.get('Content-Type', ''):
            with open(out_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=32768):
                    if chunk: f.write(chunk)
            print(f'Downloaded {fname}')
            return True
        else:
            return False
    except Exception as e:
        return False

# Download 20 files concurrently
print('Starting high-speed concurrent download...')
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    executor.map(download_file, files)
