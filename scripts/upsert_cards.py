#!/usr/bin/env python3
"""
Trello Card Upsert v2 — Auto-Credential Edition

Reads credentials from ~/.config/trello/credentials.json by default.
CLI arguments override file values if provided.

Usage (automated — no arguments needed):
  python3 upsert_cards.py --cards cards.json

Usage (with overrides):
  python3 upsert_cards.py --key KEY --token TOKEN --list-id LIST_ID --cards cards.json

Usage (dry run — validate without pushing):
  python3 upsert_cards.py --cards cards.json --dry-run

Usage (pipe JSON directly):
  python3 upsert_cards.py --cards-json '[{"title": "...", ...}]'
"""

import argparse
import json
import os
import re
import sys
import time
import requests

TRELLO_BASE = "https://api.trello.com/1"
CREDENTIALS_PATH = os.path.expanduser("~/.config/trello/credentials.json")
LABEL_COLORS = [
    "green", "yellow", "orange", "red", "purple",
    "blue", "sky", "lime", "pink", "black",
]


def load_credentials():
    """Load Trello credentials from the local config file."""
    if not os.path.exists(CREDENTIALS_PATH):
        return None
    try:
        with open(CREDENTIALS_PATH) as f:
            creds = json.load(f)
        return {
            "key": creds.get("api_key", ""),
            "token": creds.get("token", ""),
            "list_id": creds.get("default_list_id", ""),
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"WARNING: Could not parse credentials file: {e}")
        return None


def resolve_credentials(args):
    """
    Resolve credentials with priority: CLI args > credentials file.
    Returns (key, token, list_id) or exits with error.
    """
    file_creds = load_credentials() or {}

    key = args.key or file_creds.get("key", "")
    token = args.token or file_creds.get("token", "")
    list_id = args.list_id or file_creds.get("list_id", "")

    missing = []
    if not key:
        missing.append("API key (--key or credentials file)")
    if not token:
        missing.append("Token (--token or credentials file)")
    if not list_id:
        missing.append("List ID (--list-id or credentials file)")

    if missing:
        print("ERROR: Missing required credentials:")
        for m in missing:
            print(f"  - {m}")
        print(f"\nEither pass via CLI or create: {CREDENTIALS_PATH}")
        sys.exit(1)

    return key, token, list_id


def api(method, path, key, token, **kwargs):
    url = f"{TRELLO_BASE}{path}"
    params = kwargs.pop("params", {})
    params["key"] = key
    params["token"] = token
    r = requests.request(method, url, params=params, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else None


def extract_card_id(title):
    match = re.search(r"\[([A-Z]+-\d+(?:-S\d+)?)\]", title)
    return match.group(1) if match else None


def get_board_id_from_list(list_id, key, token):
    data = api("GET", f"/lists/{list_id}", key, token)
    return data["idBoard"]


def get_all_board_cards(board_id, key, token):
    return api("GET", f"/boards/{board_id}/cards", key, token,
               params={"fields": "name,desc,idLabels,shortUrl,idList", "filter": "all"})


def get_or_create_labels(board_id, label_names, key, token):
    existing_labels = api("GET", f"/boards/{board_id}/labels", key, token)
    existing = {lbl["name"].lower(): lbl["id"] for lbl in existing_labels if lbl["name"]}
    label_map = {}
    color_idx = 0
    for name in label_names:
        key_lower = name.lower()
        if key_lower in existing:
            label_map[key_lower] = existing[key_lower]
        else:
            color = LABEL_COLORS[color_idx % len(LABEL_COLORS)]
            color_idx += 1
            result = api("POST", "/labels", key, token,
                         json={"name": name, "color": color, "idBoard": board_id})
            label_map[key_lower] = result["id"]
            existing[key_lower] = result["id"]
            print(f"  + Created label '{name}' ({color})")
    return label_map


def get_card_checklists(card_id, key, token):
    return api("GET", f"/cards/{card_id}/checklists", key, token)


def delete_checklist(checklist_id, key, token):
    api("DELETE", f"/checklists/{checklist_id}", key, token)


def add_checklist(card_id, checklist_name, items, key, token):
    result = api("POST", f"/cards/{card_id}/checklists", key, token,
                 json={"name": checklist_name})
    cl_id = result["id"]
    for item in items:
        api("POST", f"/checklists/{cl_id}/checkItems", key, token,
            json={"name": item})
    return cl_id


def create_card(list_id, title, description, label_ids, key, token):
    payload = {"name": title, "desc": description or "", "idList": list_id,
               "idLabels": ",".join(label_ids) if label_ids else ""}
    return api("POST", "/cards", key, token, json=payload)


def update_card(card_id, title, description, label_ids, key, token):
    payload = {"name": title, "desc": description or "",
               "idLabels": ",".join(label_ids) if label_ids else ""}
    return api("PUT", f"/cards/{card_id}", key, token, json=payload)


def main():
    parser = argparse.ArgumentParser(
        description="Trello Card Upsert v2 — auto-credential, dry-run support"
    )
    parser.add_argument("--key", default=None, help="Trello API key (overrides credentials file)")
    parser.add_argument("--token", default=None, help="Trello API token (overrides credentials file)")
    parser.add_argument("--list-id", default=None, help="Target list ID (overrides credentials file)")
    parser.add_argument("--cards", default=None, help="Path to JSON file with card data")
    parser.add_argument("--cards-json", default=None, help="Raw JSON string with card data (alternative to --cards)")
    parser.add_argument("--dry-run", action="store_true", help="Validate JSON and credentials without pushing to Trello")
    args = parser.parse_args()

    # ── Load cards ──
    if args.cards_json:
        try:
            cards = json.loads(args.cards_json)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON string: {e}")
            sys.exit(1)
    elif args.cards:
        with open(args.cards) as f:
            cards = json.load(f)
    else:
        print("ERROR: Provide either --cards (file path) or --cards-json (raw JSON string)")
        sys.exit(1)

    if not cards:
        print("No cards found.")
        sys.exit(0)

    print(f"Found {len(cards)} card(s).\n")

    # ── Resolve credentials ──
    key, token, list_id = resolve_credentials(args)

    # ── Dry run mode ──
    if args.dry_run:
        print("DRY RUN — validating without pushing to Trello.\n")
        try:
            board_id = get_board_id_from_list(list_id, key, token)
            print(f"Credentials valid. Board ID: {board_id}")
        except Exception as e:
            print(f"Credential validation FAILED: {e}")
            sys.exit(1)

        print(f"\nCards to process:")
        for i, card in enumerate(cards):
            tag = extract_card_id(card.get("title", ""))
            cl = card.get("checklist", [])
            labels = card.get("labels", [])
            print(f"  [{i+1}] {card.get('title', 'Untitled')}")
            print(f"      Tag: {tag or 'NONE'} | Labels: {labels} | Checklist: {len(cl)} items")

        print(f"\nDRY RUN COMPLETE. {len(cards)} cards validated. No changes made to Trello.")
        sys.exit(0)

    # ── Live execution ──
    try:
        board_id = get_board_id_from_list(list_id, key, token)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in (401, 403):
            print("ERROR: Invalid API key or token.")
        elif e.response.status_code == 404:
            print("ERROR: List ID not found.")
        else:
            print(f"ERROR: {e}")
        sys.exit(1)

    print("Scanning board for existing cards...")
    board_cards = get_all_board_cards(board_id, key, token)
    existing_map = {}
    for bc in board_cards:
        tag = extract_card_id(bc.get("name", ""))
        if tag:
            existing_map[tag] = bc
    print(f"  Found {len(existing_map)} card(s) with ID tags.\n")

    all_label_names = set()
    for card in cards:
        for lbl in card.get("labels", []):
            all_label_names.add(lbl.lower())

    label_map = {}
    if all_label_names:
        print("Syncing labels...")
        label_map = get_or_create_labels(board_id, list(all_label_names), key, token)
        print()

    created = 0
    updated = 0
    failed = 0
    board_url = None

    print("=" * 60)
    print("Processing cards...")
    print("=" * 60)

    for i, card in enumerate(cards):
        title = card.get("title", f"Card {i+1}")
        description = card.get("description", "")
        label_names = [l.lower() for l in card.get("labels", [])]
        label_ids = [label_map[l] for l in label_names if l in label_map]
        checklist_items = card.get("checklist", [])
        card_tag = extract_card_id(title)
        existing = existing_map.get(card_tag) if card_tag else None

        try:
            if existing:
                trello_card_id = existing["id"]
                card_url = existing.get("shortUrl", "")
                update_card(trello_card_id, title, description, label_ids, key, token)
                old_checklists = get_card_checklists(trello_card_id, key, token)
                for old_cl in old_checklists:
                    delete_checklist(old_cl["id"], key, token)
                if checklist_items:
                    add_checklist(trello_card_id, "Acceptance Criteria", checklist_items, key, token)
                print(f"  UPDATED [{i+1}/{len(cards)}] {title}")
                print(f"          {card_url}")
                updated += 1
            else:
                result = create_card(list_id, title, description, label_ids, key, token)
                card_url = result.get("shortUrl", result.get("url", ""))
                trello_card_id = result["id"]
                if checklist_items:
                    add_checklist(trello_card_id, "Acceptance Criteria", checklist_items, key, token)
                print(f"  CREATED [{i+1}/{len(cards)}] {title}")
                print(f"          {card_url}")
                created += 1

            if not board_url and card_url:
                board_url = card_url.rsplit("/c/", 1)[0]
            time.sleep(0.2)

        except Exception as e:
            print(f"  FAILED  [{i+1}/{len(cards)}] {title}")
            print(f"          Error: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"CREATED: {created}  |  UPDATED: {updated}  |  FAILED: {failed}")
    if board_url:
        print(f"Board: {board_url}")


if __name__ == "__main__":
    main()
