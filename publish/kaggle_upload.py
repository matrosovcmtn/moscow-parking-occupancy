#!/usr/bin/env python3
"""Публикация датасета на Kaggle с полными метаданными.

Запуск:
    KAGGLE_API_TOKEN=KGAT_... python3 publish/kaggle_upload.py

Три грабли, на которые здесь уже наступили:

1. `kagglehub.dataset_upload()` создаёт датасет ПРИВАТНЫМ и без лицензии.
   Для открытого датасета это бессмысленно, поэтому берём у kagglehub только
   загрузку файлов, а запрос на создание собираем сами.

2. kagglehub 0.3.13 не понимает токены формата `KGAT_`: его `_get_auth()`
   умеет только пару username+key, а bearer — лишь внутри ноутбука Kaggle,
   и молча возвращает None. Публичные GET при этом проходят и создают
   иллюзию, что авторизация работает. Сам API bearer принимает — подставляем
   заголовок сами.

3. `ownerSlug` обязателен и не выводится из токена: без него API отвечает
   «Invalid Owner Id». Это логин на Kaggle, он может не совпадать с GitHub.
"""

import os
import sys

import requests
from kagglehub.clients import KaggleApiV1Client
from kagglehub.gcs_upload import normalize_patterns, upload_files_and_directories

SLUG = "moscow-parking-occupancy"
TITLE = "Moscow Parking Occupancy (4.6M snapshots)"
SUBTITLE = "210 municipal lots, 30-minute granularity, since March 2025"
UPLOAD_DIR = os.environ.get("KAGGLE_UPLOAD_DIR", "/tmp/kag/upload")

DESCRIPTION_PATH = os.path.join(os.path.dirname(__file__), "kaggle", "description.md")


class _BearerAuth(requests.auth.AuthBase):
    def __init__(self, token: str):
        self._token = token

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        r.headers["Authorization"] = f"Bearer {self._token}"
        return r


def main() -> int:
    token = os.environ.get("KAGGLE_API_TOKEN")
    # Логин на Kaggle не совпадает ни с GitHub, ни с Hugging Face.
    owner = os.environ.get("KAGGLE_OWNER", "danilmatrosov")
    if not token:
        print("не задан KAGGLE_API_TOKEN", file=sys.stderr)
        return 2

    KaggleApiV1Client._get_auth = lambda self: _BearerAuth(token)  # type: ignore[method-assign]

    print(f"загружаю файлы из {UPLOAD_DIR} ...", flush=True)
    info = upload_files_and_directories(
        UPLOAD_DIR,
        item_type="dataset",
        ignore_patterns=normalize_patterns(default=[".git/", ".DS_Store"], additional=None),
    )
    tokens = list(info.files)
    if not tokens:
        print("файлы не загрузились", file=sys.stderr)
        return 1
    print(f"  файлов загружено: {len(tokens)}")

    with open(DESCRIPTION_PATH, encoding="utf-8") as fh:
        description = fh.read()

    client = KaggleApiV1Client()
    exists = False
    try:
        client.get(f"/datasets/view/{owner}/{SLUG}")
        exists = True
    except Exception:
        exists = False

    if exists:
        print("датасет уже есть — создаю новую версию", flush=True)
        client.post(
            f"/datasets/create/version/{owner}/{SLUG}",
            {
                "versionNotes": os.environ.get("KAGGLE_VERSION_NOTES", "data refresh"),
                "files": [{"token": t} for t in tokens],
                "directories": info.serialize()["directories"],
            },
        )
    else:
        print("создаю датасет", flush=True)
        client.post(
            "/datasets/create/new",
            {
                "ownerSlug": owner,
                "slug": SLUG,
                "title": TITLE,
                "subtitle": SUBTITLE,
                "description": description,
                "licenseName": "CC-BY-4.0",
                "isPrivate": False,
                "files": [{"token": t} for t in tokens],
                "directories": info.serialize()["directories"],
            },
        )

    print(f"готово: https://www.kaggle.com/datasets/{owner}/{SLUG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
