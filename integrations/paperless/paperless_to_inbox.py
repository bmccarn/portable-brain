#!/usr/bin/env python3
"""Copy Paperless-ngx documents into a Portable Brain inbox as PDF + metadata/OCR sidecar."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

FIELDS = "id,title,created,added,correspondent,document_type,tags,original_file_name,archive_serial_number,page_count"


class Paperless:
    def __init__(self, url: str, token: str) -> None:
        self.base = url.rstrip("/") + "/api/"
        self.token = token

    def _request(self, path: str) -> urllib.request.Request:
        return urllib.request.Request(self.base + path, headers={"Authorization": f"Token {self.token}"})

    def get(self, path: str) -> Any:
        with urllib.request.urlopen(self._request(path), timeout=120) as response:
            return json.load(response)

    def bytes(self, path: str) -> bytes:
        with urllib.request.urlopen(self._request(path), timeout=300) as response:
            return response.read()

    def all_results(self, path: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        url: str | None = path
        while url:
            page = self.get(url)
            results.extend(page["results"])
            following = page.get("next")
            url = following.split("/api/", 1)[1] if following else None
        return results

    def names(self, kind: str) -> dict[int, str]:
        return {item["id"]: item["name"] for item in self.all_results(f"{kind}/?page_size=200")}


def build_queries(
    tags: list[str], types: list[str], correspondents: list[str], since: str | None,
    tag_ids: dict[str, int], type_ids: dict[str, int], correspondent_ids: dict[str, int],
) -> list[str]:
    """Return the document list queries whose union is the selection."""
    def ids(names: list[str], table: dict[str, int], label: str) -> list[int]:
        missing = [name for name in names if name not in table]
        if missing:
            raise SystemExit(f"unknown {label}: {', '.join(missing)}")
        return [table[name] for name in names]
    suffix = f"&page_size=100&fields={FIELDS}" + (f"&added__date__gt={since}" if since else "")
    queries: list[str] = []
    if tags:
        queries.append(f"documents/?tags__id__in={','.join(map(str, ids(tags, tag_ids, 'tag')))}{suffix}")
    if types:
        queries.append(f"documents/?document_type__id__in={','.join(map(str, ids(types, type_ids, 'document type')))}{suffix}")
    if correspondents:
        queries.append(f"documents/?correspondent__id__in={','.join(map(str, ids(correspondents, correspondent_ids, 'correspondent')))}{suffix}")
    if not queries:
        queries.append(f"documents/?ordering=created{suffix}")
    return queries


def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")[:60]


def sidecar(doc: dict[str, Any], names: dict[str, dict[int, str]], url: str, filename: str, text: str, notes: list[str]) -> str:
    lines = [
        "---",
        "captured_from: paperless-ngx",
        f"paperless_id: {doc['id']}",
        f"paperless_url: {url}/documents/{doc['id']}/details",
        f"title: {json.dumps(doc['title'])}",
        f"correspondent: {json.dumps(names['correspondents'].get(doc.get('correspondent'), ''))}",
        f"document_type: {json.dumps(names['document_types'].get(doc.get('document_type'), ''))}",
        f"tags: {json.dumps([names['tags'].get(tag, str(tag)) for tag in doc.get('tags', [])])}",
        f"document_date: {(doc.get('created') or '')[:10]}",
        f"added_to_paperless: {(doc.get('added') or '')[:19]}",
        f"original_file_name: {json.dumps(doc.get('original_file_name') or '')}",
        f"pages: {doc.get('page_count')}",
        f"file: {filename}",
        "---",
        "",
        f"# {doc['title']}",
        "",
        f"OCR text from Paperless-ngx (document {doc['id']}); the file beside this note is the archived PDF.",
        "",
    ]
    if notes:
        lines += ["## Paperless notes", "", *[f"- {note}" for note in notes], ""]
    lines += ["## Text", "", text or "(no OCR text available)", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brain", type=Path, help="brain root (documents land in <brain>/inbox/paperless)")
    parser.add_argument("--url", default=os.environ.get("PAPERLESS_URL"), help="Paperless base URL (or PAPERLESS_URL)")
    parser.add_argument("--tag", action="append", default=[], help="select by tag name (repeatable)")
    parser.add_argument("--type", action="append", default=[], help="select by document type name (repeatable)")
    parser.add_argument("--correspondent", action="append", default=[], help="select by correspondent name (repeatable)")
    parser.add_argument("--ids", nargs="*", type=int, default=[], help="select specific document ids")
    parser.add_argument("--all", action="store_true", help="select every document")
    parser.add_argument("--since", help="only documents added to Paperless after YYYY-MM-DD")
    parser.add_argument("--limit", type=int, help="capture at most this many (oldest first)")
    parser.add_argument("--dest", type=Path, help="destination folder (default: <brain>/inbox/paperless)")
    parser.add_argument("--recapture", action="store_true", help="capture documents already recorded as captured")
    parser.add_argument("--dry-run", action="store_true", help="list what would be captured and stop")
    args = parser.parse_args(argv)
    token = os.environ.get("PAPERLESS_TOKEN")
    if not args.url or not token:
        parser.error("PAPERLESS_URL (or --url) and PAPERLESS_TOKEN are required")
    if not (args.tag or args.type or args.correspondent or args.ids or args.all):
        parser.error("select documents with --tag/--type/--correspondent/--ids, or --all")
    if not (args.brain / ".portable-brain" / "profile.yaml").is_file():
        parser.error(f"not a brain: {args.brain}")
    dest = args.dest or args.brain / "inbox" / "paperless"
    state_path = args.brain / ".portable-brain" / "paperless-captured.json"
    captured: dict[str, str] = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    api = Paperless(args.url, token)
    names = {kind: api.names(kind) for kind in ("tags", "document_types", "correspondents")}
    by_name = {kind: {name: identifier for identifier, name in table.items()} for kind, table in names.items()}
    selected: dict[int, dict[str, Any]] = {}
    if args.ids:
        for identifier in args.ids:
            selected[identifier] = api.get(f"documents/{identifier}/?fields={FIELDS}")
    else:
        for query in build_queries(args.tag, args.type, args.correspondent, args.since, by_name["tags"], by_name["document_types"], by_name["correspondents"]):
            for doc in api.all_results(query):
                selected[doc["id"]] = doc
    docs = sorted(selected.values(), key=lambda doc: (doc.get("created") or "", doc["id"]))
    if not args.recapture:
        docs = [doc for doc in docs if str(doc["id"]) not in captured]
    if args.limit is not None:
        docs = docs[: args.limit]
    print(f"{len(docs)} document(s) selected" + (" (dry run)" if args.dry_run else ""))
    if args.dry_run:
        for doc in docs:
            print(f"  {doc['id']:>5}  {(doc.get('created') or '')[:10]}  {names['correspondents'].get(doc.get('correspondent'), ''):<30.30}  {doc['title'][:60]}")
        return 0
    dest.mkdir(parents=True, exist_ok=True)
    for number, doc in enumerate(docs, 1):
        base = f"{(doc.get('created') or 'undated')[:10]}-paperless-{doc['id']}-{slug(doc['title'])}"
        payload = api.bytes(f"documents/{doc['id']}/download/")
        extension = ".pdf" if payload[:4] == b"%PDF" else Path(doc.get("original_file_name") or "").suffix or ".bin"
        (dest / (base + extension)).write_bytes(payload)
        content = api.get(f"documents/{doc['id']}/?fields=content,notes")
        notes = [note.get("note", "") for note in content.get("notes") or []]
        (dest / (base + ".md")).write_text(sidecar(doc, names, args.url.rstrip("/"), base + extension, (content.get("content") or "").strip(), notes), encoding="utf-8")
        captured[str(doc["id"])] = base + extension
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(captured, indent=1, sort_keys=True), encoding="utf-8")
        print(f"  {number:>3}. {base}{extension}")
    print(f"captured {len(docs)} into {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
