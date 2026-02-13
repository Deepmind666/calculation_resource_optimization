"""Archive web snapshots with hash and headers for audit evidence.

Usage:
  python qa/archive_web_snapshots.py \
    --targets prior_art/evidence/R30_targets.json \
    --out prior_art/evidence \
    --manifest-name R30_snapshot_manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class Target:
    name: str
    url: str
    group: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def _guess_ext(content_type: Optional[str], fallback: str = ".bin") -> str:
    ct = (content_type or "").lower()
    if "html" in ct:
        return ".html"
    if "json" in ct:
        return ".json"
    if "xml" in ct:
        return ".xml"
    if "text/plain" in ct:
        return ".txt"
    return fallback


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_headers(path: Path, status: Optional[int], headers: Dict[str, str]) -> None:
    lines = [f"status: {status if status is not None else 'N/A'}"]
    for key, value in headers.items():
        lines.append(f"{key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _normalize(path: Path) -> str:
    return str(path).replace("\\", "/")


def capture(target: Target, out_root: Path, timeout_sec: int) -> Dict[str, object]:
    group_dir = out_root / target.group
    group_dir.mkdir(parents=True, exist_ok=True)

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Codex-SnapshotArchiver/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "close",
    }
    if target.headers:
        req_headers.update(target.headers)

    req = Request(target.url, method=target.method, headers=req_headers)

    rec: Dict[str, object] = {
        "name": target.name,
        "group": target.group,
        "url": target.url,
        "status": "error",
        "http_status": None,
        "content_type": None,
        "bytes": None,
        "sha256": None,
        "saved_file": None,
        "saved_headers": None,
        "saved_error_body": None,
        "error": None,
    }

    base = _safe_name(target.name)
    hdr_path = group_dir / f"{base}.headers.txt"

    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read()
            status = getattr(resp, "status", None)
            content_type = resp.headers.get("Content-Type", "")
            ext = _guess_ext(content_type, fallback=".bin")

            body_path = group_dir / f"{base}{ext}"
            body_path.write_bytes(body)
            _write_headers(hdr_path, status, dict(resp.headers.items()))

            rec.update(
                {
                    "status": "ok",
                    "http_status": status,
                    "content_type": content_type,
                    "bytes": len(body),
                    "sha256": _sha256(body),
                    "saved_file": _normalize(body_path),
                    "saved_headers": _normalize(hdr_path),
                }
            )
    except HTTPError as err:
        err_body = b""
        try:
            err_body = err.read() or b""
        except Exception:
            err_body = b""

        err_headers = dict(err.headers.items()) if getattr(err, "headers", None) else {}
        _write_headers(hdr_path, err.code, err_headers)

        rec.update(
            {
                "http_status": err.code,
                "error": f"HTTPError {err.code}: {err.reason}",
                "saved_headers": _normalize(hdr_path),
            }
        )
        if err_body:
            err_path = group_dir / f"{base}.error.html"
            err_path.write_bytes(err_body)
            rec["saved_error_body"] = _normalize(err_path)
            rec["bytes"] = len(err_body)
            rec["sha256"] = _sha256(err_body)
    except URLError as err:
        rec["error"] = f"URLError: {err.reason}"
    except Exception as err:  # pragma: no cover - defensive path
        rec["error"] = f"{type(err).__name__}: {err}"

    return rec


def load_targets(path: Path) -> List[Target]:
    data = json.loads(path.read_text(encoding="utf-8"))
    targets: List[Target] = []
    for item in data.get("targets", []):
        targets.append(
            Target(
                name=str(item["name"]),
                url=str(item["url"]),
                group=str(item["group"]),
                method=str(item.get("method", "GET")),
                headers=item.get("headers"),
            )
        )
    return targets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True, help="JSON file containing target list")
    parser.add_argument("--out", default="prior_art/evidence", help="output root directory")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    parser.add_argument("--manifest-name", default="R30_snapshot_manifest.json")
    args = parser.parse_args()

    targets_path = Path(args.targets)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    targets = load_targets(targets_path)
    results = [capture(t, out_root, args.timeout) for t in targets]

    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    manifest = {
        "captured_at": now,
        "targets_file": _normalize(targets_path),
        "items": results,
    }

    manifest_path = out_root / args.manifest_name
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for item in results if item.get("status") == "ok")
    err = len(results) - ok
    print(f"manifest={manifest_path} ok={ok} err={err}")


if __name__ == "__main__":
    main()
