#!/usr/bin/env python3
"""Fetch a bounded prefix of one pinned FineWeb/FineWeb2 parquet shard.

Uses HTTP Range requests so only the parquet footer and the first row groups
are transferred. A hard transfer cap is enforced on bytes actually received.
Only the `text` (and `id`) columns are retained, as gzip JSONL outside git.
Requires pyarrow (scratch venv); not a runtime dependency of the crate.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
import shutil
import urllib.request
from pathlib import Path

import pyarrow.parquet as parquet

SOURCES = {
    "en": ("HuggingFaceFW/fineweb", "9bb295ddab0e05d785b879661af7260fed5140fc",
           "sample/10BT/000_00000.parquet"),
    "tr": ("HuggingFaceFW/fineweb-2", "af9c13333eb981300149d5ca60a8e9d659b276b9",
           "data/tur_Latn/train/000_00000.parquet"),
}
OUT = Path("/home/agent/corpora/readable-hash-overnight")


class RangeFile:
    """Read-only seekable file over HTTP Range with a received-bytes cap."""

    def __init__(self, url, cap):
        self.url, self.cap, self.position, self.received = url, cap, 0, 0
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=60) as response:
            self.size = int(response.headers["Content-Length"])
        self.closed = False

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        base = {0: 0, 1: self.position, 2: self.size}[whence]
        self.position = base + offset
        return self.position

    def read(self, length=-1):
        if length is None or length < 0:
            length = self.size - self.position
        length = min(length, self.size - self.position)
        if length <= 0:
            return b""
        if self.received + length > self.cap:
            raise RuntimeError(f"transfer cap {self.cap} would be exceeded")
        request = urllib.request.Request(
            self.url, headers={"Range": f"bytes={self.position}-{self.position + length - 1}"})
        chunks = []
        with urllib.request.urlopen(request, timeout=120) as response:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                self.received += len(chunk)
                if self.received > self.cap:
                    raise RuntimeError("transfer cap exceeded while streaming")
                chunks.append(chunk)
        data = b"".join(chunks)
        if len(data) != length:
            raise RuntimeError("short range response")
        self.position += length
        return data

    def close(self):
        self.closed = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("language", choices=sorted(SOURCES))
    parser.add_argument("--text-bytes", type=int, default=100_000_000)
    parser.add_argument("--transfer-cap", type=int, default=400_000_000)
    args = parser.parse_args()
    if shutil.disk_usage("/").free < 25 * 10**9:
        raise SystemExit("refusing: less than 25 GB free")
    repo, revision, path = SOURCES[args.language]
    url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{path}"
    handle = RangeFile(url, args.transfer_cap)
    reader = parquet.ParquetFile(handle)
    schema = [field.name for field in reader.schema_arrow]
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{args.language}_sample.jsonl.gz"
    text_bytes = documents = groups = 0
    with gzip.open(target, "wt", encoding="utf-8", compresslevel=6) as output:
        for group in range(reader.num_row_groups):
            table = reader.read_row_group(group, columns=["id", "text"])
            groups += 1
            for doc_id, text in zip(table.column("id").to_pylist(), table.column("text").to_pylist()):
                encoded = len(text.encode("utf-8"))
                if text_bytes + encoded > args.text_bytes:
                    break
                output.write(json.dumps({"id": doc_id, "text": text}, ensure_ascii=False) + "\n")
                text_bytes += encoded
                documents += 1
            else:
                continue
            break
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest_path = OUT / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest[args.language] = {
        "dataset": repo, "revision": revision, "file": path, "url": url,
        "license": "ODC-By 1.0; subject to CommonCrawl Terms of Use",
        "shard_bytes": handle.size, "bytes_transferred": handle.received,
        "transfer_cap": args.transfer_cap, "row_groups_read": groups,
        "parquet_schema": schema, "documents": documents,
        "clean_utf8_text_bytes": text_bytes, "retained_file": str(target),
        "retained_gzip_bytes": target.stat().st_size, "retained_sha256": digest,
        "selection": "first documents in shard order up to text-byte cap (train split only)",
        "fetched_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "fetcher": "models/overnight/fetch_sample.py v1",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest[args.language], indent=2))


if __name__ == "__main__":
    os.umask(0o022)
    main()
