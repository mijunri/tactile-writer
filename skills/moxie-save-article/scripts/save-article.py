#!/usr/bin/env python3
"""Upload finished article HTML to Moxie (墨写) backend."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser(description="Save article HTML to Moxie platform")
    p.add_argument("--title", required=True, help="Article title")
    p.add_argument("--platform", default="微信公众号", help="Target platform")
    p.add_argument("--html-file", type=str, help="Path to HTML file")
    p.add_argument("--html-stdin", action="store_true", help="Read HTML from stdin")
    p.add_argument("--work-item-id", type=int, default=None, help="Tactile work item id")
    args = p.parse_args()

    base = os.environ.get("MOXIE_API_BASE", "").rstrip("/")
    token = os.environ.get("MOXIE_UPLOAD_TOKEN", "")
    if not base or not token:
        print("ERROR: MOXIE_API_BASE and MOXIE_UPLOAD_TOKEN must be set", file=sys.stderr)
        return 1

    if args.html_file:
        html = open(args.html_file, encoding="utf-8").read()
    elif args.html_stdin:
        html = sys.stdin.read()
    else:
        print("ERROR: provide --html-file or --html-stdin", file=sys.stderr)
        return 1

    if not html.strip():
        print("ERROR: empty HTML", file=sys.stderr)
        return 1

    payload = json.dumps(
        {
            "title": args.title,
            "platform": args.platform,
            "html": html,
            "work_item_id": args.work_item_id,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{base}/internal/articles/upload",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Moxie-Token": token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
            print(json.dumps(body, ensure_ascii=False, indent=2))
            return 0
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
