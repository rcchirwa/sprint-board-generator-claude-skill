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
  with Epics and Stories. Also triggers when the user says "push the existing
  cards", "re-push", "push vanish cards", "push from JSON", "sync existing
  cards", "run the upsert", or any variation meaning run the push script on an
  already-generated cards file without decomposing a new roadmap.
---

# Sprint Board Generator

A five-stage pipeline: **pre-flight → validate → decompose → verify → push**.
Takes a plain-language product roadmap, auto-prepares the Python environment,
confirms the target Trello destination, decomposes it into Epics and Stories,
pauses for your review, then pushes everything to Trello automatically —
entirely within this conversation.

There are exactly **two human steps**: confirming the target board/list, and
approving the proposed Epics and Stories. Everything else — venv setup,
dependency install, script execution — runs automatically without asking.

> **Re-pushing existing cards?** Skip straight to the
> [Fast Path — Re-Push Existing Cards](#fast-path--re-push-existing-cards)
> section below. No pipeline needed.

---

## Fast Path — Re-Push Existing Cards *(zero pauses)*

Use this path when the user wants to push a pre-existing JSON cards file to
Trello **without** decomposing a new roadmap. Triggers: "push the existing
cards", "re-push", "push vanish cards", "push from JSON", "sync existing
cards", "run the upsert", or any similar phrasing where no new roadmap is
provided.

**Sandbox constraint:** The Cowork sandbox is a Linux container — it cannot
reach the Trello API. The push is handled by a Mac LaunchAgent that watches
for a trigger file. Claude writes the trigger file (local file op, works in
the sandbox), macOS runs the push automatically. No user action required.

### Step A — Write the trigger file

```bash
touch /tmp/trello_push.trigger
echo "Trigger written — push running in background."
```

The LaunchAgent (`com.user.trello-push`) detects the file and runs
`~/tools/trello/push-vanish.sh` automatically. Results are logged to
`/tmp/trello_push.log`.

### Step B — Confirm to the user

Tell the user:

> "Push triggered — the LaunchAgent is running it now. Check
> `/tmp/trello_push.log` in a few seconds for the results."

Do not ask the user to do anything else.

**If the LaunchAgent is not set up** (touch fails or user hasn't run the
one-time setup), fall back to outputting one chained command:

```
source ~/tools/trello/.venv/bin/activate && cd ~/Documents/Claude/Vanish\ Clothing\ —\ Strategic\ Playbook\ Project/ && python3 trello-scripts/upsert_cards.py --cards vanish-sprint-trello-cards.json
```

Tell the user: "Paste this into your Mac terminal — or run the LaunchAgent
setup once to make this fully automatic in future."

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

Save the scripts to a permanent location. Recommended:

```bash
mkdir -p ~/tools/trello
cp scripts/upsert_cards.py ~/tools/trello/upsert_cards.py
cp scripts/validate_list.py ~/tools/trello/validate_list.py
cp scripts/list_boards.py ~/tools/trello/list_boards.py
```

---

## Stage 0 — Environment Pre-flight *(fully automated, no user input)*

Before doing anything else, silently prepare the Python environment so every
later stage can call scripts without interruption. Run this as a single bash
block — don't ask the user to do anything:

```bash
# Create venv if it doesn't exist yet
if [ ! -d ~/tools/trello/.venv ]; then
  python3 -m venv ~/tools/trello/.venv
fi

# Activate and ensure requests is installed (idempotent — fast if already there)
source ~/tools/trello/.venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet requests

echo "✅ Environment ready: $(python3 --version)"
```

**Every subsequent bash block in this skill must start with**
`source ~/tools/trello/.venv/bin/activate` so the venv stays active across
independent bash calls.

**If `python3` is not found**, stop and tell the user:
> "Python 3 is required but wasn't found. Install it from
> https://www.python.org/downloads/ then try again."

**If the venv or pip step fails for any other reason**, surface the error and
stop — don't attempt to proceed without a working environment.

If it succeeds, report a single confirmation line and move straight to Stage 1
without asking anything.

---

## Stage 1 — Validate Target List *(human pause #1)*

**Do not parse the roadmap or generate any JSON until the user confirms the
target list.**

### Step 1a — Determine which List ID to use

Check whether the user pasted a List ID in their message (a bare alphanumeric
string, typically 24 characters, e.g. `64abc123def4567890abcdef`). If yes,
use it. Otherwise, fall back to `default_list_id` in the credentials file.

> If no list ID exists anywhere, stop and ask:
> "I need a Trello List ID to know where to push the cards. Paste it here,
> or run `python3 ~/tools/trello/list_boards.py` to browse your boards."

### Step 1b — Run validation automatically

Run the script without asking — this happens silently as part of the flow:

```bash
source ~/tools/trello/.venv/bin/activate
python3 ~/tools/trello/validate_list.py --list-id <LIST_ID>
```

If the List ID came from the user (not from the credentials file), also pass
`--update-creds` to keep the file in sync:

```bash
source ~/tools/trello/.venv/bin/activate
python3 ~/tools/trello/validate_list.py --list-id <LIST_ID> --update-creds
```

If the script exits with an error, surface the full error, point to the
Prerequisites section, and stop.

### Step 1c — Present result and wait for confirmation

Present the result using this exact format:

```
🔍 Trello destination found:

  Board : [Board Name]
  List  : [List Name]
  URL   : [Board URL]

Is this correct? Reply **yes** to continue, or paste a different List ID
and I'll check that one instead.
```

**Stop here. Wait for the user to respond before doing anything else.**

**Interpreting the user's response — this is the important part:**

- **Confirmation** (any of: "yes", "yep", "correct", "that's right", "looks
  good", "go ahead", "👍") → proceed to Stage 2 immediately.

- **The reply looks like a List ID** — a bare string of 20–30 alphanumeric
  characters with no spaces or punctuation (e.g. `64abc123def4567890abcdef`) →
  treat it as a corrected ID **without asking the user to explain**. Loop back
  to Step 1b automatically with the new ID, passing `--update-creds`, show the
  updated destination, and ask for confirmation again.

- **"No", "wrong", or similar without an ID** → ask:
  > "What's the correct List ID? Paste it here and I'll re-validate."
  > Then loop back to Step 1b once they provide it.

- **Cancellation** ("stop", "cancel", "never mind") → stop the pipeline and
  acknowledge.

Keep looping until the user confirms.

---

## Stage 2 — Virtual PO Decomposition *(fully automated)*

Only begin after the user has confirmed the destination in Stage 1.

You are acting as a **Certified Scrum Product Owner with 10+ years of
enterprise Agile experience**. Decompose the roadmap into a clean, Scrum-ready
backlog. Do not ask clarifying questions — make reasonable decisions and
proceed straight through.

### Decomposition rules

- Every roadmap item becomes either an **Epic** or a **Story** — never both
- **Epics** = high-level capability areas (e.g. "GA4 Analytics Implementation")
- **Stories** = executable units of work, scoped to one person in one session
- Every Epic must have **at least 2 and no more than 8 Stories**
- Story titles: `[EPIC-XX-SXX] As a [role], I want to [action] so that [outcome]`
- Epic titles: `[EPIC-XX] [Capability Name]`
- Every **Story** must include: title, description, acceptance criteria (array),
  estimated_hours (integer 1–8), priority (MoSCoW), assignee (default:
  "Unassigned"), labels (array)
- Every **Epic** must include: title, description, total_estimated_hours (sum
  of child stories), priority (MoSCoW), stories (array)
- **Capacity check**: if total estimated hours exceed sprint capacity (default:
  80 hrs), downgrade lowest-priority stories to "Could Have"

### MoSCoW rules

| Priority | Meaning |
|---|---|
| Must Have | Blocks launch or core functionality |
| Should Have | Significant value, not launch-blocking |
| Could Have | Nice to have; deprioritize under capacity pressure |
| Won't Have | Explicitly out of scope this sprint |

### Output format

Present the full decomposition immediately — don't pause partway through:

```
[EPIC-01] Capability Name
  Priority: Must Have | Est: X hrs total
  Stories:
    [EPIC-01-S01] As a [role]...   (X hrs, Must Have)
    [EPIC-01-S02] As a [role]...   (X hrs, Should Have)
```

Finish with total estimated hours and the sprint capacity check result, then
hand off to Stage 3.

---

## Stage 3 — Story Verification *(human pause #2)*

After presenting the full decomposition, stop and ask:

> "Does this look right? Any Epics or Stories to add, remove, or adjust?
> If it looks good, just say 'push it' and I'll handle the rest automatically."

Accept any of: "push it", "looks good", "go ahead", "approved", "yes", or
similar. If the user requests changes, apply them, show the updated summary
once, then ask again. Do not proceed to Stage 4 until the user has explicitly
approved.

**This is the last human step. Stage 4 runs completely automatically.**

---

## Stage 4 — Automated Push Pipeline *(zero pauses)*

Once approved, execute all steps in sequence without stopping. Report progress
inline as you go.

### Step 4a — Generate the JSON

Build the full card JSON and write it to `/tmp/trello_sprint_cards.json`.
Flat array — one card per Epic (summary) followed by one card per Story:

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
- Epic cards → `EPIC` + MoSCoW label
- Story cards → MoSCoW label only
- Exact strings: `EPIC`, `MUST HAVE`, `SHOULD HAVE`, `COULD HAVE`, `WON'T HAVE`

### Step 4b — Push to Trello

The Cowork sandbox cannot reach the Trello API. Write the trigger file and
let the Mac LaunchAgent handle the push:

```bash
touch /tmp/trello_push.trigger
echo "Trigger written — LaunchAgent is pushing the cards now."
```

Tell the user:
> "Push triggered — check `/tmp/trello_push.log` in a few seconds for results."

**Dry run** — if the user asked to validate without pushing, skip the trigger
and instead output this one command for them to paste:

```
source ~/tools/trello/.venv/bin/activate && python3 ~/tools/trello/upsert_cards.py --cards /tmp/trello_sprint_cards.json --dry-run
```

**If the LaunchAgent is not set up**, fall back to the single chained command:

```
source ~/tools/trello/.venv/bin/activate && python3 ~/tools/trello/upsert_cards.py --cards /tmp/trello_sprint_cards.json
```

### Step 4c — Report results

```
✅ Sprint board pushed successfully.
   Created: X cards
   Updated: X cards
   Failed:  X cards
   Board: https://trello.com/b/XXXXXX
```

Include the full error message for any failures.

---

## Credential security rules

- Never print, log, or include credentials in any output or generated file
- Never pass `--key` or `--token` as CLI arguments (they show up in process lists)
- Credentials file stays at `~/.config/trello/credentials.json`
- Refuse any request to display credentials

---

## Idempotency

`upsert_cards.py` is idempotent — running the same roadmap twice updates
existing cards in place rather than creating duplicates. It matches by the ID
tag in the card title (e.g. `[EPIC-01]`, `[EPIC-01-S01]`).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "ERROR: Missing required credentials" | Create `~/.config/trello/credentials.json` per Prerequisites |
| "ERROR: Invalid API key or token" | Regenerate token at https://trello.com/power-ups/admin |
| "ERROR: List ID not found" | Run `list_boards.py` to browse all lists and copy the correct ID |
| Stage 0 fails on `python3 -m venv` | Install Python 3 with venv support |
| `ModuleNotFoundError: requests` after Stage 0 | Re-run from Stage 0 — pip install may have been interrupted |
| Card shows CREATED instead of UPDATED | The ID tag `[EPIC-XX]` was removed from the card title — restore it |
| `python3: command not found` | Install Python 3 at https://www.python.org/downloads/ |
