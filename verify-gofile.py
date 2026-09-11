#! /usr/bin/env python3
"""verify-gofile.py — fetch GoFile API checksums, compare with local downloaded files."""

from hashlib import sha256, md5 as _md5
from os import getenv, path
from sys import argv, exit, stderr
from time import time
from typing import Any, Iterator

from requests import Session, Timeout

GF_DOWNLOAD_DIR = getenv("GF_DOWNLOAD_DIR", ".")
GF_TOKEN = getenv("GF_TOKEN")
ACCOUNT_CACHE: dict[str, Any] = {}


def _print(msg: str) -> None:
    stderr.write(msg + "\n")
    stderr.flush()


def _wt(session: Session, acc_token: str = "") -> str:
    ua: str = str(session.headers.get("User-Agent", "Mozilla/5.0"))
    slot: int = int(time()) // 14400
    return sha256(f"{ua}::en-US::{acc_token}::{slot}::12af056dacea0b".encode()).hexdigest()


def _ensure_account(session: Session) -> None:
    if ACCOUNT_CACHE:
        return
    tok = GF_TOKEN
    if not tok:
        r = session.post(
            "https://api.gofile.io/accounts",
            headers={"X-Website-Token": _wt(session), "X-BL": "en-US"},
            timeout=20,
        ).json()
        if r.get("status") != "ok":
            _print(f"account creation failed: {r}")
            exit(1)
        tok = r["data"]["token"]
    session.cookies.set("Cookie", f"accountToken={tok}")
    session.headers.update({"Authorization": f"Bearer {tok}"})
    ACCOUNT_CACHE["token"] = tok


def _iter_files(folder_node: dict[str, Any], base: str = "") -> Iterator[tuple[str, str, str]]:
    """yield (relative_path, name, md5) for every file inside a content folder.

    The folder's own name is skipped for its children; nested folders are
    included as path components (mirrors the downloader's local layout
    ``<GF_DOWNLOAD_DIR>/<content_id>/<children...>``).
    """
    for child in folder_node.get("children", {}).values():
        if child.get("type") == "folder":
            yield from _iter_files(child, path.join(base, child["name"]))
        else:
            yield (path.join(base, child["name"]), child["name"], child.get("md5", ""))


def main() -> None:
    if len(argv) < 2:
        _print("usage: verify-gofile.py <gofile_url> [password]")
        exit(1)

    url: str = argv[1]
    password: str | None = argv[2] if len(argv) > 2 else None
    download_dir: str = GF_DOWNLOAD_DIR

    content_id = url.rstrip("/").split("/")[-1]
    if len(content_id) < 2 or not url.rstrip("/").endswith(f"/d/{content_id}"):
        _print(f"URL does not look like a GoFile content link: {url}")
        exit(1)

    session = Session()
    session.headers.update({
        "Accept-Encoding": "gzip",
        "User-Agent": "Mozilla/5.0",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "Origin": "https://gofile.io",
        "Referer": "https://gofile.io/",
    })
    _ensure_account(session)

    api_url = (
        f"https://api.gofile.io/contents/{content_id}"
        f"?cache=true&sortField=createTime&sortDirection=1"
    )
    if password:
        sha = sha256(password.encode()).hexdigest()
        api_url += f"&password={sha}"

    try:
        resp = session.get(
            api_url,
            headers={"X-Website-Token": _wt(session, ACCOUNT_CACHE["token"]), "X-BL": "en-US"},
            timeout=20,
        )
    except Timeout:
        _print("API request timed out")
        exit(1)

    data: dict = resp.json()
    if data.get("status") != "ok":
        _print(f"API error: {data}")
        exit(1)

    root = data["data"]
    if root.get("type") != "folder":
        _print("Content is a single file (root node), nothing to recurse.")
        exit(0)

    files = list(_iter_files(root))
    if not files:
        _print("No files found in content tree.")
        exit(0)

    passed = 0
    failed = 0
    for rel, name, expected_md5 in files:
        local_path = path.join(download_dir, content_id, rel)
        if not path.isfile(local_path):
            _print(f"MISSING  {rel}")
            failed += 1
            continue
        with open(local_path, "rb") as f:
            hasher = _md5()
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)
            local_hash = hasher.hexdigest()
        if local_hash == expected_md5:
            _print(f"OK       {rel}  {local_hash}")
            passed += 1
        else:
            _print(f"MISMATCH {rel}  local={local_hash}  api={expected_md5}")
            failed += 1

    _print(f"\n{passed} passed, {failed} failed")
    exit(1 if failed else 0)


if __name__ == "__main__":
    main()
