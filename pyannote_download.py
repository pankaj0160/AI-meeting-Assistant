# download_pyannote.py
# Run with: python download_pyannote.py
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("HF_TOKEN")
if not token:
    print("ERROR: HF_TOKEN not found in .env file")
    input("Press Enter to exit...")
    exit(1)

print(f"Token: {token[:15]}...")

# Step 1: test basic HuggingFace connectivity
print("\nTesting HuggingFace connection...")
try:
    import requests
    r = requests.get("https://huggingface.co/api/whoami", 
                     headers={"Authorization": f"Bearer {token}"}, timeout=10)
    print(f"Auth status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Logged in as: {data.get('name', '?')}")
    else:
        print(f"Auth failed: {r.text}")
except Exception as e:
    print(f"Connection error: {e}")

# Step 2: check model access
print("\nChecking model access...")
try:
    import requests
    r = requests.get(
        "https://huggingface.co/api/models/pyannote/speaker-diarization-3.1",
        headers={"Authorization": f"Bearer {token}"}, timeout=10
    )
    print(f"Model API status: {r.status_code}")
    if r.status_code == 200:
        print("Model access: OK")
    elif r.status_code == 403:
        print("Model access: DENIED - terms not accepted")
    else:
        print(f"Response: {r.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Step 3: try download with huggingface_hub directly
print("\nAttempting model file download...")
try:
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id  = "pyannote/speaker-diarization-3.1",
        filename = "config.yaml",
        token    = token,
    )
    print(f"Downloaded config to: {path}")
    print("\nAccess confirmed! Now downloading full pipeline...")
    
    from pyannote.audio import Pipeline
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=token,
    )
    print("\nDownload complete! Diarization is ready.")
    
except Exception as e:
    print(f"\nERROR: {e}")
    print("\nTry setting this environment variable and run again:")
    print(f"  set HF_TOKEN={token}")
    print("  python download_pyannote.py")

input("\nPress Enter to exit...")