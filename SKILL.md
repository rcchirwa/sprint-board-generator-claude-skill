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

A three-stage pipeline: **decompose → review → push**. Takes a plain-language
product roadmap, runs it through a Virtual Product Owner persona to produce
structured Epics and Stories, pauses for your approval, then pushes idempotent
cards to a live Trello board — entirely within this conversation.

The only human step is the review. Everything else is automated.

---

## Prerequisites (first time only)

### 1. Credentials file

The push script reads credentials from a local file — no need to paste keys into
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

Save `upsert_cards.py` to a permanent location. The recommended path:

```bash
mkdir -p ~/tools/trello
cp scripts/upsert_cards.py ~/tools/trello/upsert_cards.py
```

---

## Stage 1 — Virtual PO Decomposition

You are acting as a **Certified Scrum Product Owner with 10+ years of enterprise
Agile experience**. Your job is to decompose the roadmap the user provides into a
clean, Scrum-ready backlog of Epics and Stories following these rules exactly.

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

### Output format for this stage

Present the decomposition in a readable summary — not raw JSON. Use this template
for each Epic:

```
[EPIC-01] Capability Name
  Priority: Must Have | Est: X hrs total
  Stories:
    [EPIC-01-S01] As a [role]...   (X hrs, Must Have)
    [EPIC-01-S02] As a [role]...   (X hrs, Should Have)
```

---

## Stage 2 — Verification (the only human step)

After presenting the decomposition, **stop and ask**:

> "Does this look right? Any Epics or Stories to add, remove, or adjust before I
> push to Trello? If it looks good, just say 'push it'."

Wait for explicit approval. Accept any of: "push it", "looks good", "go ahead",
"approved", "yes", or similar. If the user requests changes, apply them, show the
updated summary once, then ask for confirmation again before proceeding.

**Do not proceed to Stage 3 until the user has explicitly approved.**

---

## Stage 3 — Venv Setup, JSON Generation & Trello Push

Once approved, complete these steps in sequence without pausing.

### Step 3a — Set up the virtual environment

Check whether a venv already exists at `~/tools/trello/.venv`. Create it if not,
then activate it and ensure `requests` is installed:

```bash
if [ ! -d ~/tools/trello/.venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv ~/tools/trello/.venv
fi

source ~/tools/trello/.venv/bin/activate
pip install requests --quiet
echo "Venv ready: $(python3 --version)"
```

If `python3` is not found, tell the user and stop. Do not attempt to install Python.

### Step 3b — Generate the JSON

Build the full card JSON and write it to `/tmp/trello_sprint_cards.json`.

The JSON is a flat array of card objects. Generate one card per Epic (as a summary
card) followed by one card per Story, in Epic order. Use this exact structure:

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

### Step 3c — Run the upsert script

```bash
source ~/tools/trello/.venv/bin/activate
python3 ~/tools/trello/upsert_cards.py --cards /tmp/trello_sprint_cards.json
```

The script reads credentials automatically from `~/.config/trello/credentials.json`.
No need to pass `--key`, `--token`, or `--list-id` as arguments.

**If the credentials file is missing**, tell the user and point them to the
Prerequisites section above. Do not attempt to read or prompt for credentials.

**Dry run option** — if the user passed a `--dry-run` flag or asked to validate
without pushing, run:

```bash
source ~/tools/trello/.venv/bin/activate
python3 ~/tools/trello/upsert_cards.py --cards /tmp/trello_sprint_cards.json --dry-run
```

### Step 3d — Report results

After the script completes, tell the user:
- How many cards were **created** vs **updated** (idempotent — safe to re-run)
- Any cards that **failed**, with the error message
- A direct link to the Trello board (extracted from the card URLs in script output)

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
| "ERROR: List ID not found" | Run `list_boards.py` to find the correct ID |
| Card shows CREATED instead of UPDATED | The ID tag `[EPIC-XX]` was removed from the Trello card title — restore it |
| `ModuleNotFoundError: requests` | The venv step failed; re-run Stage 3a manually |
| `python3: command not found` | Install Python 3 at https://www.python.org/downloads/ |
