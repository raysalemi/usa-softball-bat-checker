#!/usr/bin/env python3
"""
Fetch the latest USA Softball Certified Bats HTML table and Non-Approved Bat
List PDFs directly from USA Softball, and rebuild bats.json if any bat data
has changed.

Uses only the Python standard library so it runs anywhere (including GitHub
Actions) without installing dependencies.
"""

from __future__ import annotations

import html as html_lib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zlib
from datetime import datetime

APPROVED_URL = "https://usa.asasoftball.com/e/equipmentdetail.asp"
APPROVED_POST_DATA = {
    "manufacturerid": "all",
    "queryFlag": "1",
    "equipid": "1",
    "levelFlag": "1",
}

BANNED_1PAGE_URL = "https://usa.asasoftball.com/e/BB1P2000.asp"
BANNED_PICS_2000_URL = "https://usa.asasoftball.com/e/build_batlist_w_pics_2000.asp"
BANNED_PICS_2004_URL = "https://usa.asasoftball.com/e/build_batlist_w_pics_2004.asp"

BATS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bats.json")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def http_fetch(url: str, post_data: dict | None = None, timeout: int = 45) -> bytes:
    encoded = None
    headers = {"User-Agent": USER_AGENT}
    if post_data is not None:
        encoded = urllib.parse.urlencode(post_data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=encoded, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} fetching {url}")
        return resp.read()


def parse_approved_html(raw_bytes: bytes) -> list[dict]:
    html = raw_bytes.decode("latin-1", errors="replace")
    rows = re.findall(
        r"<tr\s+height=35[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE
    )
    approved = []
    seen = {}

    for row in rows:
        cols = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
        if len(cols) < 5:
            continue
        cleaned = [
            html_lib.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ").strip()
            for c in cols[:5]
        ]
        _, manufacturer, model, description, last_update = cleaned
        if not manufacturer and not model and not description:
            continue

        entry = {
            "model": model,
            "manufacturer": manufacturer,
            "name": description,
            "status": "APPROVED",
            "last_update": last_update,
        }

        # Deduplicate exact (manufacturer, model, name) tuples, keeping newest date
        dedup_key = (
            manufacturer.lower(),
            model.lower(),
            description.lower(),
        )
        if dedup_key in seen:
            prev = seen[dedup_key]
            if _parse_date(last_update) >= _parse_date(prev.get("last_update", "")):
                prev["last_update"] = last_update
                prev["manufacturer"] = manufacturer
                prev["model"] = model
                prev["name"] = description
        else:
            seen[dedup_key] = entry
            approved.append(entry)

    return approved


def _parse_date(date_str: str) -> datetime:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return datetime.min


def _extract_pdf_text_blocks(pdf_bytes: bytes, font_tag: str) -> list[dict[int, dict[int, str]]]:
    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("Expected PDF payload from USA Softball banned bat endpoint")

    pages = []
    for stream in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL):
        try:
            dec = zlib.decompress(stream).decode("latin-1")
        except Exception:
            continue
        if font_tag not in dec:
            continue
        by_y: dict[int, dict[int, str]] = {}
        for block in re.findall(r"BT\s*(.*?)\s*ET", dec, re.DOTALL):
            if font_tag not in block:
                continue
            m_pos = re.search(r"(\d+)\s+(\d+)\s+Td", block)
            m_txt = re.search(r"\((.*)\)\s*Tj", block)
            if m_pos and m_txt:
                x, y = int(m_pos.group(1)), int(m_pos.group(2))
                txt = (
                    m_txt.group(1)
                    .replace(r"\(", "(")
                    .replace(r"\)", ")")
                    .replace(r"\\", "\\")
                    .strip()
                )
                by_y.setdefault(y, {})[x] = txt
        if by_y:
            pages.append(by_y)
    return pages


def parse_banned_1page_pdf(pdf_bytes: bytes) -> list[tuple[str, str]]:
    pairs = []
    for by_y in _extract_pdf_text_blocks(pdf_bytes, "/F1 9 Tf"):
        for y in sorted(by_y.keys(), reverse=True):
            row = by_y[y]
            for mx, nx in ((10, 90), (290, 370), (570, 650)):
                if mx in row and nx in row:
                    pairs.append((row[mx], row[nx]))
    return pairs


def parse_banned_pics_pdf(pdf_bytes: bytes) -> list[tuple[str, str]]:
    pairs = []
    for by_y in _extract_pdf_text_blocks(pdf_bytes, "/F1 16 Tf"):
        for y in sorted(by_y.keys(), reverse=True):
            row = by_y[y]
            if 36 in row and 186 in row:
                pairs.append((row[36], row[186]))
    return pairs


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def split_new_banned_fullname(fullname: str) -> tuple[str, str]:
    """Split a newly-discovered PDF Bat Name string into (model, name)."""
    if " - " in fullname:
        left, right = [p.strip() for p in fullname.split(" - ", 1)]
        # In USA Softball PDFs (e.g. "Battle Ground - ESBCA242", "SkyBolt - MFE6"),
        # the right side is typically the alphanumeric model code.
        if re.search(r"\d", right) and not re.search(r"\d", left):
            return right, left
        return left, right

    parts = fullname.split(None, 1)
    if len(parts) == 2 and re.search(r"\d", parts[0]):
        return parts[0], parts[1]

    return fullname, fullname


def build_banned_entries(
    banned_pairs: list[tuple[str, str]], existing_bats: list[dict]
) -> list[dict]:
    existing_banned = [b for b in existing_bats if b.get("status") == "BANNED"]
    used_indices: set[int] = set()
    result: list[dict] = []

    # Deduplicate (mfg, fullname) preserving order across all 3 PDFs
    unique_pairs: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for mfg, fullname in banned_pairs:
        key = (_norm(mfg), fullname.strip().lower())
        if key not in seen_pairs:
            seen_pairs.add(key)
            unique_pairs.append((mfg.strip(), fullname.strip()))

    for mfg, fullname in unique_pairs:
        tokens = [t for t in re.split(r"[\s()]+", fullname.lower()) if t]
        matched_idx = None

        # Pass 1: exact token or full-string match on curated model
        for idx, bat in enumerate(existing_banned):
            if idx in used_indices or _norm(bat.get("manufacturer", "")) != _norm(mfg):
                continue
            bm = bat.get("model", "").strip().lower()
            if bm and (bm == fullname.lower() or bm in tokens):
                matched_idx = idx
                break

        # Pass 2: substring match on curated model
        if matched_idx is None:
            for idx, bat in enumerate(existing_banned):
                if idx in used_indices or _norm(bat.get("manufacturer", "")) != _norm(mfg):
                    continue
                bm = bat.get("model", "").strip().lower()
                if bm and bm in fullname.lower():
                    matched_idx = idx
                    break

        if matched_idx is not None:
            used_indices.add(matched_idx)
            curated = dict(existing_banned[matched_idx])
            curated["status"] = "BANNED"
            result.append(curated)
        else:
            model, name = split_new_banned_fullname(fullname)
            result.append(
                {
                    "model": model,
                    "manufacturer": mfg,
                    "name": name,
                    "status": "BANNED",
                }
            )

    # Keep any manually added BANNED entries that weren't in the PDFs just in case
    for idx, bat in enumerate(existing_banned):
        if idx not in used_indices:
            preserved = dict(bat)
            preserved["status"] = "BANNED"
            result.append(preserved)

    return result


def strip_meta(bats: list[dict]) -> list[dict]:
    return [b for b in bats if b.get("status") != "INFO"]


def main() -> int:
    if os.path.exists(BATS_JSON_PATH):
        with open(BATS_JSON_PATH, "r", encoding="utf-8") as f:
            existing_bats = json.load(f)
    else:
        existing_bats = []

    print("Fetching USA Softball Certified Bats table...")
    approved_raw = http_fetch(APPROVED_URL, post_data=APPROVED_POST_DATA)
    approved_entries = parse_approved_html(approved_raw)
    print(f"  Parsed {len(approved_entries)} approved bat entries.")

    if len(approved_entries) < 3500:
        raise RuntimeError(
            f"Safety check failed: expected >= 3500 approved bats, got {len(approved_entries)}"
        )

    print("Fetching USA Softball Non-Approved Bat List PDFs...")
    p1 = parse_banned_1page_pdf(http_fetch(BANNED_1PAGE_URL))
    p2 = parse_banned_pics_pdf(http_fetch(BANNED_PICS_2000_URL))
    p3 = parse_banned_pics_pdf(http_fetch(BANNED_PICS_2004_URL))
    print(f"  Parsed banned lists: PDF1={len(p1)}, PDF2={len(p2)}, PDF3={len(p3)}")

    all_banned_pairs = p1 + p2 + p3
    if len(all_banned_pairs) < 40:
        raise RuntimeError(
            f"Safety check failed: expected >= 40 banned bat entries across PDFs, got {len(all_banned_pairs)}"
        )

    banned_entries = build_banned_entries(all_banned_pairs, existing_bats)

    # Ensure BANNED always overrides APPROVED if a model appears on both lists
    banned_keys = {
        (_norm(b.get("manufacturer", "")), _norm(b.get("model", "")))
        for b in banned_entries
        if b.get("model")
    }
    filtered_approved = [
        b
        for b in approved_entries
        if (_norm(b.get("manufacturer", "")), _norm(b.get("model", "")))
        not in banned_keys
    ]

    new_records = banned_entries + filtered_approved
    old_records = strip_meta(existing_bats)

    today_str = datetime.now().strftime("%Y-%m-%d")
    old_meta = next((b for b in existing_bats if b.get("status") == "INFO"), {})

    if new_records == old_records and old_meta.get("_version") == "V02":
        print("No changes in USA Softball bat lists since last sync.")
        return 0

    system_header = {
        "_version": "V02",
        "model": "SYSTEM",
        "manufacturer": "SYSTEM",
        "name": "Database Version",
        "status": "INFO",
        "last_checked": today_str,
    }

    final_data = [system_header] + new_records
    with open(BATS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=4)
        f.write("\n")

    print(
        f"Updated bats.json: {len(banned_entries)} BANNED, "
        f"{len(filtered_approved)} APPROVED (last_checked={today_str})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
