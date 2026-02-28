# ticktick-cli

A Python 3.10+ CLI and small library for the TickTick Global Open API (OAuth2).

## Features

- OAuth2 login via local callback server
- Project list and task CRUD
- Task listing with `--today`, `--overdue`, and `--next N` filters
- JSON output for automation

## Setup (WSL)

1. Install Python 3.10+ and build tools:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

2. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install the package in editable mode:

```bash
pip install -e .
```

## Register an App in TickTick Developer Center

1. Go to the TickTick Developer Center and create a new app.
2. Set the redirect URI to match your local callback server (default: `http://localhost:8000/callback`).
3. Copy the Client ID and Client Secret into environment variables.

## Configuration

Environment variables:

- `TICKTICK_CLIENT_ID`
- `TICKTICK_CLIENT_SECRET`
- `TICKTICK_REDIRECT_URI` (default: `http://localhost:8000/callback`)
- `TICKTICK_TOKEN_PATH` (default: `~/.config/ticktick/token.json`)
- `TICKTICK_DEFAULT_TZ` (default: `Europe/Moscow`)

Example:

```bash
export TICKTICK_CLIENT_ID="your-client-id"
export TICKTICK_CLIENT_SECRET="your-client-secret"
export TICKTICK_REDIRECT_URI="http://localhost:8000/callback"
```

## Usage

Login (starts a local callback server and prints the auth URL):

```bash
tt auth login
```

Check status:

```bash
tt auth status
```

List projects:

```bash
tt projects list
```

List tasks:

```bash
tt tasks list --today
```

Create a task:

```bash
# Due time includes timezone offset
tt tasks create --project PROJECT_ID --title "Write docs" --due "2026-03-01T09:00:00-05:00" --priority medium

# Friendly reminders (default: before due time)
tt tasks create --project PROJECT_ID --title "Standup" --due "2026-03-01T10:00:00" --remind 10m --remind 1h

# Absolute reminder time (converted to relative trigger)
tt tasks create --project PROJECT_ID --title "Call" --due "2026-03-01T10:00:00" --remind at:2026-03-01T09:50:00
```

Complete a task:

```bash
tt tasks complete TASK_ID --project PROJECT_ID
```

Delete a task:

```bash
tt tasks delete TASK_ID --project PROJECT_ID
```

Update a task:

```bash
# Set reminders (friendly)
tt tasks update TASK_ID --project PROJECT_ID --title "Updated title" --remind 10m

# Or pass raw OpenAPI trigger strings
tt tasks update TASK_ID --project PROJECT_ID --remind "TRIGGER:-PT10M"
```

## Notes

- Tokens are stored as JSON at `TICKTICK_TOKEN_PATH`.
- If the API returns HTTP 401, re-run `tt auth login`.
- Refresh tokens are stored if returned, but refresh flow is not implemented.

## Tests

Run the minimal unit tests:

```bash
python -m unittest -v
```
