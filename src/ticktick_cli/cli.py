from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from .api import TickTickClient, UnauthorizedError
from .auth import delete_token, load_token, login
from .config import Settings
from .dates import filter_tasks_by_due, format_ticktick_datetime
from .reminders import parse_reminders

app = typer.Typer(help="TickTick Global Open API CLI")
auth_app = typer.Typer(help="Authentication commands")
projects_app = typer.Typer(help="Project commands")
tasks_app = typer.Typer(help="Task commands")
app.add_typer(auth_app, name="auth")
app.add_typer(projects_app, name="projects")
app.add_typer(tasks_app, name="tasks")

console = Console()


@app.callback()
def main() -> None:
    """TickTick CLI."""


def _client() -> TickTickClient:
    settings = Settings.from_env()
    return TickTickClient(settings=settings)


@auth_app.command("status")
def auth_status() -> None:
    settings = Settings.from_env()
    token_data = load_token(settings.token_path)
    if not token_data:
        print("Not logged in.")
        raise typer.Exit(code=1)
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")
    obtained_at = token_data.get("obtained_at")
    print("Logged in.")
    print(f"Token path: {settings.token_path}")
    print(f"Access token present: {bool(access_token)}")
    if expires_in and obtained_at:
        expiry = datetime.fromtimestamp(obtained_at + expires_in)
        print(f"Expires at: {expiry.isoformat()}")


@auth_app.command("login")
def auth_login(timeout: int = typer.Option(300, help="Seconds to wait for callback")) -> None:
    settings = Settings.from_env()
    try:
        token = login(settings, timeout=timeout)
    except Exception as exc:
        console.print(f"[red]Login failed:[/red] {exc}")
        raise typer.Exit(code=1)
    print("Login successful.")
    print(f"Token saved to: {settings.token_path}")
    if token.expires_in:
        print(f"Expires in: {token.expires_in} seconds")


@auth_app.command("logout")
def auth_logout() -> None:
    settings = Settings.from_env()
    if delete_token(settings.token_path):
        print("Token removed.")
    else:
        print("No token found.")


@projects_app.command("list")
def projects_list(json_out: bool = typer.Option(False, "--json", help="Output raw JSON")) -> None:
    client = _client()
    try:
        projects = client.list_projects()
    except UnauthorizedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    if json_out:
        print(json.dumps(projects, indent=2))
        return
    table = Table(title="Projects")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Closed")
    for project in projects:
        table.add_row(
            str(project.get("id", "")),
            str(project.get("name", "")),
            str(project.get("closed", "")),
        )
    console.print(table)


def _collect_tasks(client: TickTickClient, project_id: Optional[str]) -> tuple[list[dict], dict[str, str]]:
    projects = []
    if project_id:
        projects = [{"id": project_id, "name": project_id}]
    else:
        projects = client.list_projects()
    tasks: list[dict] = []
    project_names: dict[str, str] = {}
    for project in projects:
        pid = project.get("id")
        if not pid:
            continue
        project_names[pid] = project.get("name") or pid
        data = client.get_project_data(pid)
        tasks.extend(data.get("tasks", []))
    return tasks, project_names


@tasks_app.command("list")
def tasks_list(
    today: bool = typer.Option(False, "--today", help="Tasks due today"),
    overdue: bool = typer.Option(False, "--overdue", help="Tasks overdue"),
    next_days: Optional[int] = typer.Option(None, "--next", help="Tasks due in next N days"),
    project: Optional[str] = typer.Option(None, "--project", help="Project ID"),
    json_out: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    client = _client()
    try:
        tasks, project_names = _collect_tasks(client, project)
    except UnauthorizedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    tasks = filter_tasks_by_due(tasks, today=today, overdue=overdue, next_days=next_days)

    if json_out:
        print(json.dumps(tasks, indent=2))
        return

    table = Table(title="Tasks")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Project")
    table.add_column("Due")
    table.add_column("Status")
    for task in tasks:
        pid = task.get("projectId")
        table.add_row(
            str(task.get("id", "")),
            str(task.get("title", "")),
            str(project_names.get(pid, pid or "")),
            str(task.get("dueDate", "")),
            "completed" if task.get("status") == 2 else "open",
        )
    console.print(table)


@tasks_app.command("create")
def tasks_create(
    project: str = typer.Option(..., "--project", help="Project ID"),
    title: str = typer.Option(..., "--title", help="Task title"),
    content: Optional[str] = typer.Option(None, "--content", help="Task content"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (ISO8601)"),
    tz: Optional[str] = typer.Option(None, "--tz", help="IANA timezone name"),
    priority: Optional[str] = typer.Option(None, "--priority", help="none|low|medium|high"),
    remind: Optional[list[str]] = typer.Option(None, "--remind", help="Reminder trigger, repeatable"),
) -> None:
    settings = Settings.from_env()
    client = TickTickClient(settings=settings)
    payload: dict = {"projectId": project, "title": title}
    if content:
        payload["content"] = content
    tz_effective = tz or settings.default_tz
    if due:
        due_str, tz_used = format_ticktick_datetime(due, tzname=tz_effective, force_tz=bool(tz))
        payload["dueDate"] = due_str
        if tz_used:
            payload["timeZone"] = tz_used
    if priority:
        priority_map = {"none": 0, "low": 1, "medium": 3, "high": 5}
        if priority not in priority_map:
            raise typer.BadParameter("priority must be one of: none, low, medium, high")
        payload["priority"] = priority_map[priority]

    parsed_reminders = parse_reminders(remind, due=due, tzname=tz_effective)
    if parsed_reminders:
        payload["reminders"] = parsed_reminders
    try:
        created = client.create_task(payload)
    except UnauthorizedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    print(json.dumps(created, indent=2))


@tasks_app.command("complete")
def tasks_complete(
    task_id: str = typer.Argument(..., help="Task ID"),
    project: str = typer.Option(..., "--project", help="Project ID"),
) -> None:
    client = _client()
    try:
        client.complete_task(project, task_id)
    except UnauthorizedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    print("Task completed.")


@tasks_app.command("delete")
def tasks_delete(
    task_id: str = typer.Argument(..., help="Task ID"),
    project: str = typer.Option(..., "--project", help="Project ID"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
) -> None:
    if not yes:
        confirmed = typer.confirm(f"Delete task {task_id} in project {project}?")
        if not confirmed:
            raise typer.Exit(code=0)
    client = _client()
    try:
        client.delete_task(project, task_id)
    except UnauthorizedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    print("Task deleted.")


@tasks_app.command("update")
def tasks_update(
    task_id: str = typer.Argument(..., help="Task ID"),
    project: str = typer.Option(..., "--project", help="Project ID"),
    title: Optional[str] = typer.Option(None, "--title", help="Task title"),
    content: Optional[str] = typer.Option(None, "--content", help="Task content"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (ISO8601)"),
    tz: Optional[str] = typer.Option(None, "--tz", help="IANA timezone name"),
    priority: Optional[str] = typer.Option(None, "--priority", help="none|low|medium|high"),
    remind: Optional[list[str]] = typer.Option(None, "--remind", help="Reminder trigger, repeatable"),
) -> None:
    settings = Settings.from_env()
    client = TickTickClient(settings=settings)
    payload: dict = {"id": task_id, "projectId": project}
    if title:
        payload["title"] = title
    if content:
        payload["content"] = content
    tz_effective = tz or settings.default_tz
    if due:
        due_str, tz_used = format_ticktick_datetime(due, tzname=tz_effective, force_tz=bool(tz))
        payload["dueDate"] = due_str
        if tz_used:
            payload["timeZone"] = tz_used
    if priority:
        priority_map = {"none": 0, "low": 1, "medium": 3, "high": 5}
        if priority not in priority_map:
            raise typer.BadParameter("priority must be one of: none, low, medium, high")
        payload["priority"] = priority_map[priority]

    if remind is not None:
        parsed_reminders = parse_reminders(remind, due=due, tzname=tz_effective)
        payload["reminders"] = parsed_reminders or []
    try:
        updated = client.update_task(task_id, payload)
    except UnauthorizedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    print(json.dumps(updated, indent=2))


@tasks_app.command("convert-to-note")
def tasks_convert_to_note(
    task_id: str = typer.Argument(..., help="Task ID to convert"),
    project: str = typer.Option(..., "--project", help="Project ID (or 'inbox')"),
    delete_old: bool = typer.Option(
        False,
        "--delete-old",
        help="Delete the original task after creating the NOTE copy",
    ),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompts"),
    backup_dir: str = typer.Option(
        "~/.config/ticktick/backups",
        "--backup-dir",
        help="Directory to store JSON backups with timestamps",
    ),
) -> None:
    """Create a NOTE item with the same title/content/desc/tags, optionally delete the original task."""

    client = _client()

    try:
        data = client.get_project_data(project)
    except UnauthorizedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    tasks: list[dict] = data.get("tasks", [])
    src = next((t for t in tasks if t.get("id") == task_id), None)
    if not src:
        console.print(f"[red]Task not found:[/red] {task_id} (project={project})")
        raise typer.Exit(code=1)

    if str(src.get("kind", "")).upper() == "NOTE":
        print("Task is already a NOTE. Nothing to do.")
        print(json.dumps(src, indent=2))
        raise typer.Exit(code=0)

    payload = {
        "projectId": project,
        "title": src.get("title") or "",
        "content": src.get("content") or "",
        "desc": src.get("desc") or "",
        "tags": src.get("tags") or [],
        "kind": "NOTE",
    }

    try:
        created = client.create_task(payload)
    except UnauthorizedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    # Backup (source + created) with timestamp
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = Path(backup_dir).expanduser() / f"convert-to-note-{task_id}-{ts}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_doc = {
        "timestamp": ts,
        "project": project,
        "taskId": task_id,
        "createdId": created.get("id"),
        "source": src,
        "created": created,
    }
    backup_path.write_text(json.dumps(backup_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Created NOTE copy:")
    print(json.dumps(created, indent=2))
    print(f"Backup saved: {backup_path}")

    if delete_old:
        if not yes:
            confirmed = typer.confirm(f"Delete original task {task_id} in project {project}?")
            if not confirmed:
                raise typer.Exit(code=0)
        try:
            client.delete_task(project, task_id)
        except UnauthorizedError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)
        print("Original task deleted.")
