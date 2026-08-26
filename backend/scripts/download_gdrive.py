import os
import sys
import gdown

# Force UTF-8 stdout for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

folder_url = "https://drive.google.com/drive/folders/1k_2fJxQhFdh6_oTCz_mtzBvx03ci0p4c"
output_dir = r"D:\recruitment_platform\gdrive_resumes"
os.makedirs(output_dir, exist_ok=True)

print("Starting Google Drive batch resume download...")
try:
    gdown.download_folder(url=folder_url, output=output_dir, quiet=False, use_cookies=False)
    downloaded = os.listdir(output_dir)
    print(f"Successfully downloaded {len(downloaded)} resumes to {output_dir}!")
except Exception as e:
    print(f"Download notice: {e}")
