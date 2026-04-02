#!/usr/bin/env python3
"""
MinerU PDF to Markdown converter.

Usage: python mineru_parse.py <pdf_file_path>

Uses MinerU precise parsing API (vlm model) to convert PDF to Markdown.
Token is read from MINERU_TOKEN env var or MinerU.md file.
"""

import requests
import time
import sys
import os
import zipfile
import io

MINERU_API = "https://mineru.net/api/v4"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def get_token():
    """Get MinerU API token from env or MinerU.md file."""
    token = os.environ.get("MINERU_TOKEN", "").strip()
    if token:
        return token

    mineru_md = os.path.join(PROJECT_DIR, "MinerU.md")
    if os.path.exists(mineru_md):
        with open(mineru_md, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("eyJ"):
                    return line

    print("ERROR: No MinerU token found. Set MINERU_TOKEN env or add token to MinerU.md")
    sys.exit(1)


def upload_file(file_path, token):
    """Upload local file via batch upload API."""
    file_name = os.path.basename(file_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = {
        "files": [{"name": file_name}],
        "model_version": "vlm",
        "enable_formula": True,
        "enable_table": True,
        "language": "en",
    }

    print(f"[1/4] Requesting upload URL for {file_name}...")
    resp = requests.post(f"{MINERU_API}/file-urls/batch", headers=headers, json=data)
    result = resp.json()

    if result["code"] != 0:
        print(f"ERROR: Get upload URL failed: {result['msg']}")
        sys.exit(1)

    batch_id = result["data"]["batch_id"]
    upload_url = result["data"]["file_urls"][0]
    print(f"  Batch ID: {batch_id}")

    print(f"[2/4] Uploading {file_name}...")
    with open(file_path, "rb") as f:
        put_resp = requests.put(upload_url, data=f)
        if put_resp.status_code not in (200, 201):
            print(f"ERROR: Upload failed, HTTP {put_resp.status_code}")
            sys.exit(1)

    print("  Upload complete.")
    return batch_id


def poll_result(batch_id, token, timeout=600, interval=5):
    """Poll batch result until all tasks are done."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    url = f"{MINERU_API}/extract-results/batch/{batch_id}"

    start = time.time()
    consecutive_errors = 0
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            consecutive_errors = 0
            result = resp.json()

            if result["code"] != 0:
                print(f"ERROR: Poll failed: {result['msg']}")
                sys.exit(1)

            for item in result["data"]["extract_result"]:
                state = item["state"]
                elapsed = int(time.time() - start)

                if state == "done":
                    print(f"  [{elapsed}s] Parsing complete!")
                    return item["full_zip_url"]

                if state == "failed":
                    print(f"ERROR: Parsing failed: {item.get('err_msg', 'Unknown')}")
                    sys.exit(1)

                progress = item.get("extract_progress")
                if progress:
                    extracted = progress.get("extracted_pages", "?")
                    total = progress.get("total_pages", "?")
                    print(f"  [{elapsed}s] {state} | {extracted}/{total} pages")
                else:
                    print(f"  [{elapsed}s] {state}...")

        except (requests.ConnectionError, requests.Timeout) as e:
            consecutive_errors += 1
            elapsed = int(time.time() - start)
            print(f"  [{elapsed}s] Network error (retry {consecutive_errors}): {e}")
            if consecutive_errors >= 10:
                print(f"ERROR: Too many network errors. Batch ID: {batch_id}")
                print(f"  You can manually query later with this batch_id.")
                sys.exit(1)

        time.sleep(interval)

    print(f"ERROR: Timeout after {timeout}s")
    sys.exit(1)


def download_and_extract(zip_url, output_path):
    """Download zip and extract full.md to output_path."""
    print("[4/4] Downloading and extracting Markdown...")
    resp = requests.get(zip_url)
    if resp.status_code != 200:
        print(f"ERROR: Download failed, HTTP {resp.status_code}")
        sys.exit(1)

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        md_files = [f for f in z.namelist() if f.endswith("full.md")]
        if not md_files:
            print(f"ERROR: No full.md in zip. Contents: {z.namelist()}")
            sys.exit(1)

        md_content = z.read(md_files[0]).decode("utf-8")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python mineru_parse.py <pdf_file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    file_name = os.path.basename(file_path)
    base_name = os.path.splitext(file_name)[0]
    output_path = os.path.join(PROJECT_DIR, "papers", f"{base_name}.md")

    token = get_token()
    batch_id = upload_file(file_path, token)

    print("[3/4] Waiting for MinerU to parse...")
    zip_url = poll_result(batch_id, token)

    md_path = download_and_extract(zip_url, output_path)
    print(f"\nDone! Markdown saved to: {md_path}")


if __name__ == "__main__":
    main()
