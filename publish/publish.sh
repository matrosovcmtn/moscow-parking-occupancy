#!/usr/bin/env bash
#
# Публикация датасета на Kaggle и Hugging Face.
#
#   KAGGLE_API_TOKEN=KGAT_… ./publish/publish.sh kaggle
#   HF_TOKEN=hf_…            ./publish/publish.sh hf
#
# Логины у всех трёх площадок разные, поэтому зашиты значениями по умолчанию:
#   GitHub        matrosovcmtn
#   Kaggle        danilmatrosov   (KAGGLE_OWNER)
#   Hugging Face  matrosovdani    (HF_OWNER)
#
# GitHub остаётся каноническим источником: обе площадки — зеркала, которые
# нужны только для находимости. Перезаливать их достаточно раз в месяц,
# еженедельный крон их не трогает.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-}"
STAGE="$REPO_DIR/.publish-stage"

die() { printf '\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

case "$TARGET" in
kaggle)
    [ -n "${KAGGLE_API_TOKEN:-}" ] || die "не задан KAGGLE_API_TOKEN"
    python3 -c 'import kagglehub, pandas, pyarrow' 2>/dev/null \
        || die "нужны пакеты: pip install kagglehub pandas pyarrow"

    # Kaggle не умеет вложенные папки в датасете, поэтому месячные файлы
    # склеиваем в один parquet — заодно так удобнее для пользователя.
    rm -rf "$STAGE"; mkdir -p "$STAGE"
    python3 - "$REPO_DIR" "$STAGE" <<'PY'
import sys, glob, pandas as pd
repo, stage = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(f"{repo}/data/occupancy_*.parquet"))
df = pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)
df.sort_values(["time", "parking_id"], inplace=True, kind="mergesort")
df.to_parquet(f"{stage}/occupancy.parquet", compression="zstd", index=False)
pd.read_parquet(f"{repo}/data/parking_spots.parquet").to_parquet(
    f"{stage}/parking_spots.parquet", compression="zstd", index=False)
print(f"  склеено {len(files)} месяцев, {len(df):,} строк")
PY

    KAGGLE_UPLOAD_DIR="$STAGE" KAGGLE_OWNER="${KAGGLE_OWNER:-danilmatrosov}" \
        python3 "$REPO_DIR/publish/kaggle_upload.py"
    rm -rf "$STAGE"
    ;;

hf)
    python3 -c 'import huggingface_hub' 2>/dev/null || die "нет huggingface_hub: pip install huggingface_hub"
    [ -n "${HF_TOKEN:-}" ] || die "не задан HF_TOKEN (huggingface.co → Settings → Access Tokens, право write)"

    python3 - "$REPO_DIR" <<'PY'
import os, sys
from huggingface_hub import HfApi
repo_dir = sys.argv[1]
api = HfApi(token=os.environ["HF_TOKEN"])
repo_id = f"{os.environ.get('HF_OWNER', 'matrosovdani')}/moscow-parking-occupancy"

api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
# Карточка датасета: YAML-шапка включает встроенный просмотрщик HF.
api.upload_file(
    path_or_fileobj=f"{repo_dir}/publish/huggingface/README.md",
    path_in_repo="README.md", repo_id=repo_id, repo_type="dataset")
api.upload_folder(
    folder_path=f"{repo_dir}/data", path_in_repo="data",
    repo_id=repo_id, repo_type="dataset", allow_patterns=["*.parquet"],
    commit_message="data refresh")
print(f"  https://huggingface.co/datasets/{repo_id}")
PY
    ;;

*)
    die "укажи площадку: kaggle | hf"
    ;;
esac

echo "готово: $TARGET"
