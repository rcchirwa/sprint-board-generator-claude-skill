# Sprint Board Generator — Claude Skill

Turn a plain-language product roadmap into a fully structured Trello sprint board — without leaving Claude.

You describe what you're building. Claude breaks it down into Epics and Stories, shows you the plan for review, and pushes the cards directly to your Trello board once you say go.

---

## What it does

Most people write roadmaps in plain English — a bullet list, a few paragraphs, a rough plan. Getting that into a properly structured Trello board usually means hours of manual card creation.

This skill automates that entire process in three steps:

**1. Decompose** — Claude reads your roadmap and acts as a Virtual Product Owner. It breaks your input into Epics (big themes) and Stories (individual tasks), writes them in proper Agile user story format, assigns hour estimates, and prioritises everything using MoSCoW (Must Have / Should Have / Could Have / Won't Have).

**2. Review** — Before anything touches Trello, Claude shows you the full proposed breakdown and asks for your approval. You can request changes, remove cards, or adjust priorities. Nothing is pushed until you say so.

**3. Push** — Once you approve, Claude generates the Trello cards and pushes them to your board automatically. If you run the same roadmap again after making changes, it updates the existing cards rather than creating duplicates.

---

## What you'll need before using this skill

### A Claude Desktop account
This skill runs inside Claude Desktop (the desktop app). It won't work in the Claude web browser interface.

### A Trello account and board
You need a free Trello account at [trello.com](https://trello.com) and at least one board set up where you want the cards to go.

### A Trello Epic Power-Up (highly recommended)
Epics do not work out of the box on Trello boards. To get full Epic functionality — including Epic grouping, progress tracking, and Epic-level views — you need to install a Trello Power-Up that adds Epic support. **Hello Epics** is a popular option. Without a Power-Up like this, Epic cards will appear on your board as regular cards with no Epic-specific behaviour.

To add Hello Epics (or a similar Power-Up):
1. Open your Trello board
2. Click **Power-Ups** in the board menu
3. Search for **Hello Epics** (or your preferred Epic booster)
4. Click **Add** to install it on your board

### Two API keys — Trello
The skill connects to Trello on your behalf. You need to generate a personal API key and token from Trello (it's free and takes about 2 minutes):

1. Go to [trello.com/power-ups/admin](https://trello.com/power-ups/admin)
2. Create or select a Power-Up
3. Copy your **API Key**
4. Click **Token** next to the API key, authorise access, and copy your **Token**

> These are your personal credentials — never share them publicly or commit them to a GitHub repository.

### A credentials file on your computer
Once you have your API key and token, create a file at this exact path on your Mac:

```
~/.config/trello/credentials.json
```

With these contents (fill in your own values):

```json
{
  "api_key": "YOUR_TRELLO_API_KEY",
  "token": "YOUR_TRELLO_TOKEN",
  "default_list_id": "YOUR_TARGET_LIST_ID"
}
```

To find your List ID (the specific column on your board where cards should land), run the included `list_boards.py` script:

```bash
python3 scripts/list_boards.py --key YOUR_KEY --token YOUR_TOKEN
```

It will print all your boards and their list IDs. Copy the one you want.

### Python 3 and the `requests` library
The skill runs a small Python script to push cards to Trello. You need Python 3 installed on your Mac (most Macs already have it — run `python3 --version` in Terminal to check). The skill will automatically create a virtual environment and install the `requests` library the first time it runs.

---

## How to use it

Once everything above is set up, using the skill is just a conversation.

Open Claude Desktop and say something like:

> *"Here's my roadmap for next sprint — decompose it and push it to Trello."*

Then paste your roadmap — it can be a paragraph, a bullet list, a structured doc, whatever you have. Claude will handle the rest.

You can also say:

- *"Turn this product brief into a sprint board"*
- *"Generate Trello cards from this roadmap"*
- *"Run the PO pipeline on this and push to Trello"*

Claude will always pause and show you the proposed cards before pushing anything. The only thing you need to do mid-process is review and approve.

---

## What the cards look like on your Trello board

Each Epic becomes a summary card, followed by individual Story cards. Every Story card includes:

- A user story title in the format: *As a [role], I want to [action] so that [outcome]*
- A description with context
- An acceptance criteria checklist
- An estimated number of hours
- A MoSCoW priority label
- An assignee field (defaults to "Unassigned")

Running the same roadmap twice won't create duplicate cards — the skill detects existing cards by their ID tag and updates them in place.

---

## Running in dry-run mode

If you want to see what cards would be generated without pushing anything to Trello, ask Claude to do a dry run:

> *"Generate the sprint cards from this roadmap but don't push to Trello yet — just show me what would be created."*

---

## Files included in this skill

| File | What it does |
|---|---|
| `SKILL.md` | The skill instructions Claude reads when you invoke it |
| `scripts/upsert_cards.py` | The script that pushes cards to Trello (creates or updates) |
| `scripts/list_boards.py` | Utility to find your Trello board and list IDs |

---

## Troubleshooting

**"Missing required credentials"** — Check that your `~/.config/trello/credentials.json` file exists and contains valid values.

**"Invalid API key or token"** — Your token may have expired. Regenerate it at [trello.com/power-ups/admin](https://trello.com/power-ups/admin).

**"List ID not found"** — Run `list_boards.py` to confirm the list ID in your credentials file is correct.

**Card shows as CREATED instead of UPDATED on re-run** — The ID tag (e.g. `[EPIC-01]`) was manually removed from the card title on Trello. Restore it and re-run.

---

## A note on security

Your Trello API key and token give anyone who has them full access to your Trello boards. Keep them in your local credentials file only. Never paste them into a Claude conversation, commit them to a repository, or share them with anyone.

---

## Related projects

This skill is part of a broader AI workflow engineering stack. Related tools:

- **Shopify MCP Server** — connects Claude directly to a Shopify store for product, order, and inventory management via natural language

---

*Built by Robert Chirwa · March 2026*
*Part of the AI Workflow Engineer portfolio*
