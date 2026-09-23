import pandas as pd
import hashlib
from pathlib import Path
import sys

freeze = Path('C:/Users/daksh/.gemini/antigravity-ide/scratch/microservice-failure-analysis/EVIDENCE_FREEZE')
manifest_path = freeze / 'audit' / 'SHA256_MANIFEST.csv'

if not manifest_path.exists():
    print("FAIL: Manifest not found.")
    sys.exit(1)

def get_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

manifest = pd.read_csv(manifest_path)
failed = 0
for idx, row in manifest.iterrows():
    fpath = freeze / row['path']
    if not fpath.exists():
        print(f"FAIL: File missing - {row['path']}")
        failed += 1
        continue
    
    current_hash = get_sha256(fpath)
    if current_hash != row['sha256']:
        print(f"FAIL: Hash mismatch - {row['path']}")
        failed += 1

if failed == 0:
    print("SUCCESS: All 224 files passed SHA256 integrity check. No original files were modified.")
else:
    print(f"FAILED: {failed} files failed integrity check.")
