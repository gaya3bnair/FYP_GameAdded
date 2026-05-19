# download_models.py
import os
from huggingface_hub import snapshot_download

HF_USERNAME = os.getenv("HF_USERNAME")
HF_TOKEN    = os.getenv("HF_TOKEN")

def download_if_missing():
    if not os.path.exists("ser_model"):
        print("[STARTUP] Downloading SER model...")
        snapshot_download(
            repo_id=f"{HF_USERNAME}/ser-model",
            local_dir="ser_model",
            token=HF_TOKEN,
        )
        print("[STARTUP] SER model downloaded.")

    if not os.path.exists("reward_model"):
        print("[STARTUP] Downloading reward model...")
        snapshot_download(
            repo_id=f"{HF_USERNAME}/ears-reward-model",
            local_dir="reward_model",
            token=HF_TOKEN,
        )
        print("[STARTUP] Reward model downloaded.")

if __name__ == "__main__":
    download_if_missing()