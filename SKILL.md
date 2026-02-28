---
name: ticktick
description: Use TickTick Open API for task management (list, create, complete, delete tasks and projects). Enables daily planning and task capture via the TickTick CLI.
metadata:
  {
    openclaw: { emoji: "✅", requires: { bins: ["python3", "pip"], files: ["~/projects/ticktick-cli"] } }
  }
---

# TickTick Skill

This skill enables the agent to interact with a user's TickTick account via the `ticktick-cli` CLI tool.

## Tool Interface

Use the `exec` tool to run TickTick CLI commands:

```bash
cd ~/projects/ticktick-cli && . .venv/bin/activate && tt <command>
```

Or if the package is installed globally or in PATH:
```bash
tt <command>
```

## Environment Variables

The skill expects these environment variables (already configured on this system):

- `TICKTICK_CLIENT_ID` — OAuth client ID from TickTick Developer Center
- `TICKTICK_CLIENT_SECRET` — OAuth client secret
- `TICKTICK_DEFAULT_TZ` — default timezone (default: Europe/Moscow)
- `TICKTICK_REDIRECT_URI` — OAuth callback URL (default: http://localhost:8000/callback)

Token is stored at `~/.config/ticktick/token.json` (no re-login needed unless expired).

## Available Commands

### Authentication

```bash
# Check auth status
tt auth status

# Re-login (if token expired)
tt auth login

# Logout (clear token)
tt auth logout
```

### Projects

```bash
# List all projects
tt projects list

# List projects in JSON (for automation)
tt projects list --json
```

### Tasks

```bash
# List tasks due today
tt tasks list --today

# List overdue tasks
tt tasks list --overdue

# List tasks due in next N days
tt tasks list --next 7

# List tasks in a specific project (use project name or ID, or "inbox")
tt tasks list --project inbox
tt tasks list --project "Project Name"
tt tasks list --project 6916c7a9c71c710000000082

# List tasks in JSON (for parsing)
tt tasks list --today --json
tt tasks list --overdue --json

# Create a task
tt tasks create --project inbox --title "Task title" --priority medium
tt tasks create --project "Project Name" --title "Task with due" --due "2026-03-01T10:00:00" --remind 10m

# Complete a task
tt tasks complete <task-id> --project <project-id-or-name>

# Delete a task
tt tasks delete <task-id> --project <project-id-or-name>

# Update a task
tt tasks update <task-id> --project <project-id-or-name> --title "New title" --priority high

# Convert a task into a NOTE (creates a NOTE copy; optionally deletes the original)
tt tasks convert-to-note <task-id> --project <project-id-or-name>
tt tasks convert-to-note <task-id> --project <project-id-or-name> --delete-old
```

## Reminder Syntax

Friendly reminder formats (converted to TickTick triggers):

- `10m` — 10 minutes before due time (default, means "before")
- `-10m` — same as above (explicit "before")
- `+10m` — 10 minutes after due time
- `1h`, `2h` — hours before/after
- `1d`, `2d` — days before/after
- `at:2026-03-01T09:50:00` — absolute time (converted to relative to due date)

Examples:
```bash
# Remind 10 minutes before
tt tasks create --project inbox --title "Standup" --due "2026-03-01T10:00:00" --remind 10m

# Remind 1 hour before AND 10 minutes before
tt tasks create --project inbox --title "Call" --due "2026-03-01T15:00:00" --remind 1h --remind 10m
```

## Priority Values

- `none` — 0
- `low` — 1
- `medium` — 3
- `high` — 5

## Common Patterns for Daily Planning

1. **Fetch today's tasks:**
   ```bash
   tt tasks list --today --json
   ```

2. **Fetch overdue tasks:**
   ```bash
   tt tasks list --overdue --json
   ```

3. **Fetch next 7 days:**
   ```bash
   tt tasks list --next 7 --json
   ```

4. **Fetch Inbox (unprocessed tasks):**
   ```bash
   tt tasks list --project inbox --json
   ```

5. **Create a task in Inbox with reminder:**
   ```bash
   tt tasks create --project inbox --title "Review emails" --due "2026-03-01T09:00:00" --remind 15m
   ```

## Notes

- This skill assumes the TickTick CLI is installed at `~/projects/ticktick-cli`.
- The virtual environment must be activated before running `tt` commands.
- The underlying HTTP client includes basic retries for transient failures (timeouts / 429 / 5xx).
- `tt tasks convert-to-note ...` writes a timestamped backup JSON to `~/.config/ticktick/backups` by default.
- Tasks without a due date won't appear in `--today` or `--overdue` filters.
- Use JSON output (`--json`) for programmatic parsing in automation flows.
