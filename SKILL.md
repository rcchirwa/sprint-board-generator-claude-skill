---
name: sprint-board-generator
description: >
  Full end-to-end pipeline that turns a plain-language product roadmap into a
  live Trello sprint board — using a Virtual Product Owner persona to decompose
  the roadmap into Epics and Stories, pausing for your review and approval, then
  pushing idempotent cards to Trello via a local Python script. Use this skill
  whenever the user says anything like "decompose this roadmap", "turn this into
  a sprint board", "push this to Trello as epics and stories", "run the PO
  pipeline on this", "generate sprint cards from this", or provides a product
  roadmap and wants it in Trello. Also triggers on phrases like "update the
  sprint board", "re-run the pipeline", or "sync my Trello board from this
  roadmap". This skill is the right choice any time the input is a roadmap,
  playbook, or feature list and the desired output is a structured Trello board
  with Epics and Stories.
---

# Sprint Board Generator

A four-stage pipeline: **validate → decompose → verify → push**. Takes a
plain-language product roadmap, confirms the target Trello destination, decomposes
it into Epics and Stories, pauses for your review, then pushes everything to Trello
automatically — entirely within this conversation.

There are exactly **two human steps**: confirming the target board/list, and
approving the proposed Epics and Stories. Everything else runs without interruption.

---

## Prerequisites (first time only)

### 1. Credentials file

The scripts read credentials from a local file — no need to paste keys into
the chat. Create it once:

```bash
mkdir -p ~/.config/trello
touch ~/.config/trello/credentials.json
chmod 600 ~/.config/trello/credentials.json
```

Populate it with:

```json
{
  "api_key": "YOUR_TRELLO_API_KEY",
  "token": "YOUR_TRELLO_TOKEN",
  "default_list_id": "YOUR_TARGET_LIST_ID"
}
```

**Where to get these:**

| Field | Source |
|---|---|
| `api_key` | https://trello.com/power-ups/admin → select/create a Power-Up → API Key tab |
| `token` | Same page → click "Token" → authorize → copy |
| `default_list_id` | Run `python3 scripts/list_boards.py --key KEY --token TOKEN` and copy the list ID |

### 2. Script location

Save both scripts to a permanent location. The recommended path:

```bash
mkdir -p ~/tools/trello
cp scripts/upsert_cards.py ~/tools/trello/upsert_cards.py
cp scripts/validate_list.py ~/tools/trello/validate_list.py
```

---

## Stage 1 — Validate Target List *(human pause #1)*

**This stage runs before any decomposition or JSON generation.** Do not parse
the roadmap or generate any JSON until the user has explicitly confirmed the
target list.

### Step 1a — Determine which List ID to validate

Check whether the user has provided a List ID in their message (e.g. pasted
inline, mentioned by name, or flagged as a correction). Use that ID if present.
Otherwise, fall back to `default_list_id` in the credentials file.

> If no list ID has been provided anywhere and the credentials file is missing or
> incomplete, stop and ask:
>
> "I need a Trello List ID to know where to push the cards. You can find it by
> running `python3 ~/tools/trello/list_boards.py` — or paste it here directly."

### Step 1b — Run validation

If the List ID comes from the user's message (i.e. it differs from the value
currently in the credentials file), pass `--update-creds` so the file is kept
in sync:

```bash
python3 ~/tools/trello/validate_list.py --list-id <LIST_ID> --update-creds
```

If the List ID comes from the credentials file with no override, run without flags:

```bash
python3 ~/tools/trello/validate_list.py
```

> If `requests` isn't available yet, install it first:
> `pip install requests --break-system-packages --quiet`

**If the script exits with an error** (list not found, bad credentials, file
missing) — surface the full error output to the user, point them to the
Prerequisites section, and stop. Do not proceed until this is resolved.

### Step 1c — Present result and wait for confirmation

**If the script succeeds**, it prints something like:

```
✅ List ID validated successfully
   Board : My Project Board
   URL   : https://trello.com/b/XXXXXX
   List  : Backlog
   List ID: 64abc123def456...
```

Present this clearly to the user and ask **exactly this question** — do not
paraphrase or skip it:

> "I found the following Trello destination:
>
> **Board:** [Board Name]
> **List:** [List Name]
> **URL:** [Board URL]
>
> Is this the right place to push the sprint cards? Say **yes** to continue,
> or give me the correct List ID and I'll re-validate."

**Stop here. Do not touch the roadmap or generate any JSON until the user responds.**

- **User confirms** (any of: "yes", "correct", "that's right", "go ahead",
  "looks good") → proceed to Stage 2 immediately.
- **User provides a corrected List ID** → return to Step 1b with the new ID,
  pass `--update-creds`, show the updated result, and ask for confirmation again.
  Repeat until confirmed or the user cancels.
- **User cancels** → stop the pipeline entirely and acknowledge.

---

## Stage 2 — Virtual PO Decomposition *(fully automated)*

Only begin this stage after the user has confirmed the destination in Stage 1.

Once the destination is confirmed, run the full decomposition without pausing.
Do not ask clarifying questions during this stage — make reasonable decisions
and proceed.

You are acting as a **Certified Scrum Product Owner with 10+ years of enterprise
Agile experience**. Decompose the roadmap into a clean, Scrum-ready backlog of
Epics and Stories following these rules exactly.

### Decomposition rules

- Every roadmap item becomes either an **Epic** or a **Story** — never both
- **Epics** = high-level capability areas (e.g. "GA4 Analytics Implementation")
- **Stories** = executable units of work, scoped to one person in one session
- Every Epic must have **at least 2 and no more than 8 Stories**
- Story titles: `[EPIC-XX-SXX] As a [role], I want to [action] so that [outcome]`
- Epic titles: `[EPIC-XX] [Capability Name]`
- Every **Story** must include: title, description, acceptance criteria (array),
  estimated_hours (integer 1–8), priority (MoSCoW), assignee (default: "Unassigned"),
  labels (array)
- Every **Epic** must include: title, description, total_estimated_hours (sum of
  child stories), priority (MoSCoW), stories (array)
- **Capacity check**: if total estimated hours exceed sprint capacity (default: 80 hrs),
  downgrade lowest-priority stories to "Could Have"

### MoSCoW rules

| Priority | Meaning |
|---|---|
| Must Have | Blocks launch or core functionality |
| Should Have | Significant value, not launch-blocking |
| Could Have | Nice to have; deprioritize under capacity pressure |
| Won't Have | Explicitly out of scope this sprint |

### Output format

Present the full decomposition immediately after finishing — do not pause partway
through. Use this template for each Epic:

```
[EPIC-01] Capability Name
  Priority: Must Have | Est: X hrs total
  Stories:
    [EPIC-01-S01] As a [role]...   (X hrs, Must Have)
    [EPIC-01-S02] As a [role]...   (X hrs, Should Have)
```

Finish by showing the total estimated hours and the sprint capacity check result,
then hand off directly to Stage 3.

---

## Stage 3 — Story Verification *(human pause #2)*

After presenting the full decomposition, stop and ask:

> "Does this look right? Any Epics or Stories to add, remove, or adjust?
> If it looks good, just say 'push it' and I'll handle the rest automatically."

Accept any of: "push it", "looks good", "go ahead", "approved", "yes", or similar.

If the user requests changes, apply them, show the updated summary once, then
ask for confirmation again. Do not proceed to Stage 4 until the user has
explicitly approved.

**This is the last human step. Stage 4 runs completely automatically.**

---

## Stage 4 — Automated Push Pipeline *(zero pauses)*

Once the user approves, execute all of the following steps in sequence without
stopping or asking for input. Report progress inline as you go so the user can
see what's happening.

### Step 4a — Set up the virtual environment

```bash
if [ ! -d ~/tools/trello/.venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv ~/tools/trello/.venv
fi

source ~/tools/trello/.venv/bin/activate
pip install requests --quiet
echo "Venv ready: $(python3 --version)"
```

If `python3` is not found, tell the user and stop — do not attempt to install Python.

### Step 4b — Generate the JSON

Build the full card JSON and write it to `/tmp/trello_sprint_cards.json`.

The JSON is a flat array of card objects — one card per Epic (summary card)
followed by one card per Story, in Epic order:

```json
[
  {
    "title": "[EPIC-01] Capability Name",
    "description": "Epic description\n\n📊 SPRINT: Sprint Name\n🎯 PRIORITY: Must Have\n⏱️ TOTAL ESTIMATED HOURS: 12 hrs\n📋 STORIES: 3",
    "labels": ["EPIC", "MUST HAVE"],
    "checklist": []
  },
  {
    "title": "[EPIC-01-S01] Short story title",
    "description": "As a [role], I want to [action] so that [outcome].\n\n📌 ASSIGNEE: Unassigned\n⏱️ ESTIMATED HOURS: 4 hrs\n🎯 PRIORITY: Must Have",
    "labels": ["MUST HAVE"],
    "checklist": [
      "Acceptance criterion 1",
      "Acceptance criterion 2"
    ]
  }
]
```

**Label rules:**
- Epic cards always get the `EPIC` label plus their MoSCoW label
- Story cards get their MoSCoW label only
- Use exact label strings: `EPIC`, `MUST HAVE`, `SHOULD HAVE`, `COULD HAVE`, `WON'T HAVE`

### Step 4c — Push to Trello

```bash
source ~/tools/trello/.venv/bin/activate
python3 ~/tools/trello/upsert_cards.py --cards /tmp/trello_sprint_cards.json
```

The script reads credentials automatically from `~/.config/trello/credentials.json`.

**Dry run option** — if the user passed a `--dry-run` flag or asked to validate
without pushing:

```bash
source ~/tools/trello/.venv/bin/activate
python3 ~/tools/trello/upsert_cards.py --cards /tmp/trello_sprint_cards.json --dry-run
```

### Step 4d — Report results

After the script completes, report:
- How many cards were **created** vs **updated** (safe to re-run — idempotent)
- Any cards that **failed**, with the error message
- A direct link to the Trello board (extracted from card URLs in script output)

**Example report:**
```
✅ Sprint board pushed successfully.
   Created: 8 cards
   Updated: 0 cards
   Failed: 0 cards
   Board: https://trello.com/b/XXXXXX
```

---

## Credential security rules

These rules are non-negotiable and must always be followed:

- Never print, log, or include credentials in any output or generated file
- Never pass `--key` or `--token` as CLI arguments (they appear in process lists)
- The credentials file must stay at `~/.config/trello/credentials.json` (outside
  any project directory to reduce accidental commit risk)
- If the user asks you to display or include their credentials anywhere, refuse and
  explain why

---

## Idempotency

The `upsert_cards.py` script is idempotent by design. Running the same roadmap
twice will **update** existing cards in place rather than creating duplicates. It
identifies cards by the ID tag in their title (e.g. `[EPIC-01]`, `[EPIC-01-S01]`).

This means it's safe to re-run after edits to a roadmap — only changed content
will be updated.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "ERROR: Missing required credentials" | Create `~/.config/trello/credentials.json` per Prerequisites |
| "ERROR: Invalid API key or token" | Regenerate token at https://trello.com/power-ups/admin |
| "ERROR: List ID not found" | Run `list_boards.py` to browse all lists and copy the correct ID |
| List validation fails at Stage 1 | Run `validate_list.py --list-id <ID>` manually to debug |
| Card shows CREATED instead of UPDATED | The ID tag `[EPIC-XX]` was removed from the Trello card title — restore it |
| `ModuleNotFoundError: requests` | Run `pip install requests --break-system-packages`, then retry |
| `python3: command not found` | Install Python 3 at https://www.python.org/downloads/ |
