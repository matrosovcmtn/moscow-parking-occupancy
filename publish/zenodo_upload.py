#!/usr/bin/env python3
"""Выкладка датасета на Zenodo: запись, файлы, публикация, DOI.

Запуск:
    ZENODO_TOKEN=... python3 publish/zenodo_upload.py            # боевой
    ZENODO_TOKEN=... ZENODO_HOST=sandbox.zenodo.org python3 ...  # песочница

Токен делается на https://zenodo.org/account/settings/applications/tokens/new/
и должен иметь ОБА права:
  deposit:write    создание записи и загрузка файлов
  deposit:actions  публикация и создание новой версии
Одного deposit:write не хватает: опубликовать им нельзя.

Метаданные берутся из .zenodo.json в корне репозитория. Обязательные поля для
upload_type=dataset: title, creators, description, access_right, license.

Повторный запуск при уже существующей записи создаёт НОВУЮ ВЕРСИЮ: у неё свой
DOI, а общий DOI записи остаётся прежним, и ссылка на него всегда ведёт на
последнюю версию. Идентификатор прошлой записи кладётся в .zenodo-deposition.
"""
import glob
import json
import os
import pathlib
import sys

import requests

REPO = pathlib.Path(__file__).resolve().parent.parent
HOST = os.environ.get("ZENODO_HOST", "zenodo.org")
API = f"https://{HOST}/api"
STATE = REPO / ".zenodo-deposition"


def die(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def check(resp, what: str, ok=(200, 201, 202)):
    if resp.status_code not in ok:
        die(f"{what}: HTTP {resp.status_code}\n{resp.text[:600]}")
    return resp.json() if resp.content else {}


def main() -> int:
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        die("не задан ZENODO_TOKEN")
    auth = {"Authorization": f"Bearer {token}"}
    meta = json.loads((REPO / ".zenodo.json").read_text())

    files = sorted(glob.glob(str(REPO / "data" / "*.parquet")))
    if not files:
        die("в data/ нет parquet-файлов")
    size = sum(os.path.getsize(f) for f in files)
    print(f"файлов к выкладке: {len(files)}, объём {size/1e6:.1f} МБ")
    if size > 50e9 or len(files) > 100:
        die("превышен предел Zenodo: 50 ГБ и 100 файлов на запись")

    previous = STATE.read_text().strip() if STATE.exists() else ""
    if previous:
        print(f"запись уже есть ({previous}), создаю новую версию")
        r = check(requests.post(f"{API}/deposit/depositions/{previous}/actions/newversion",
                                headers=auth, timeout=120), "newversion")
        dep_id = r["links"]["latest_draft"].rstrip("/").split("/")[-1]
        dep = check(requests.get(f"{API}/deposit/depositions/{dep_id}", headers=auth, timeout=60),
                    "чтение черновика")
        # Файлы прошлой версии переносятся автоматически, и старые надо убрать:
        # иначе в новой версии окажутся оба набора.
        for f in dep.get("files", []):
            requests.delete(f"{API}/deposit/depositions/{dep_id}/files/{f['id']}",
                            headers=auth, timeout=60)
    else:
        dep = check(requests.post(f"{API}/deposit/depositions", headers=auth, json={},
                                  timeout=120), "создание записи")
        dep_id = dep["id"]
        print(f"создана запись {dep_id}")

    bucket = dep["links"]["bucket"]
    for path in files:
        name = os.path.basename(path)
        with open(path, "rb") as fh:
            check(requests.put(f"{bucket}/{name}", data=fh, headers=auth, timeout=1800),
                  f"загрузка {name}")
        print(f"  загружен {name}")

    check(requests.put(f"{API}/deposit/depositions/{dep_id}",
                       headers={**auth, "Content-Type": "application/json"},
                       data=json.dumps({"metadata": meta}), timeout=120), "метаданные")

    published = check(requests.post(f"{API}/deposit/depositions/{dep_id}/actions/publish",
                                    headers=auth, timeout=300), "публикация")
    STATE.write_text(str(dep_id) + "\n")

    doi = published.get("doi") or published.get("metadata", {}).get("doi", "")
    concept = published.get("conceptdoi", "")
    print(f"\nопубликовано: {published['links'].get('record_html', '')}")
    print(f"DOI этой версии: {doi}")
    if concept:
        print(f"общий DOI записи (всегда последняя версия): {concept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
