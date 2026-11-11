from pathlib import Path

from huggingface_hub import snapshot_download

REPO_ID = "AgamiAI/Indian-Bank-Statements"
ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "ml" / "data" / "external" / "agami"
INCLUDE_ALL_PDFS = False

patterns = ["README.md", "train/**/*.json"]
if INCLUDE_ALL_PDFS:
    patterns.append("train/**/*.pdf")
else:
    patterns += [f"train/**/0000{i}.pdf" for i in range(1, 4)]

TARGET.mkdir(parents=True, exist_ok=True)
snapshot_download(
    repo_id=REPO_ID,
    repo_type="dataset",
    local_dir=str(TARGET),
    allow_patterns=patterns,
)

files = [p for p in TARGET.rglob("*") if p.is_file() and ".cache" not in p.parts]
json_files = [p for p in files if p.suffix == ".json"]
pdf_files = [p for p in files if p.suffix == ".pdf"]
total_mb = sum(p.stat().st_size for p in files) / 1_000_000

print(f"saved to: {TARGET}")
print(f"json files: {len(json_files)} | pdf files: {len(pdf_files)} | total size: {total_mb:,.1f} MB")
print("subfolders:", sorted({p.parent.name for p in json_files}))