#!/usr/bin/env python3
"""
List all Trello boards and their lists with IDs.
Run this once to find the List ID you want to push cards to.
Usage: python3 list_boards.py --key KEY --token TOKEN
"""

import argparse
import requests

TRELLO_BASE = "https://api.trello.com/1"


def main():
    parser = argparse.ArgumentParser(description="List Trello boards and lists")
    parser.add_argument("--key", required=True, help="Trello API key")
    parser.add_argument("--token", required=True, help="Trello API token")
    args = parser.parse_args()

    params = {"key": args.key, "token": args.token}

    try:
        r = requests.get(f"{TRELLO_BASE}/members/me/boards", params=params)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in (401, 403):
            print("❌ Invalid API key or token. Check your credentials at https://trello.com/power-ups/admin")
        else:
            print(f"❌ API error: {e}")
        return

    boards = r.json()
    print(f"\nFound {len(boards)} board(s):\n")

    for board in boards:
        if board.get("closed"):
            continue
        print(f"📋 {board['name']}")
        print(f"   Board ID: {board['id']}")
        print(f"   URL: {board['shortUrl']}")

        lists_r = requests.get(f"{TRELLO_BASE}/boards/{board['id']}/lists", params=params)
        if lists_r.ok:
            for lst in lists_r.json():
                print(f"     └─ {lst['name']}")
                print(f"           List ID: {lst['id']}")
        print()


if __name__ == "__main__":
    main()
