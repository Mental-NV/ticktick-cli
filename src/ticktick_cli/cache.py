from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


class JsonFileCache:
    def __init__(self, path: Path, ttl_seconds: int) -> None:
        self.path = path
        self.ttl_seconds = max(0, ttl_seconds)

    def load(self, *, allow_stale: bool = False) -> Any | None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError:
            return None

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        fetched_at = payload.get("fetched_at")
        data = payload.get("data")
        if not isinstance(fetched_at, (int, float)):
            return None

        if not allow_stale and self.ttl_seconds >= 0 and time.time() - float(fetched_at) > self.ttl_seconds:
            return None
        return data

    def save(self, data: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        document = {"fetched_at": time.time(), "data": data}
        fd, temp_path = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_path, self.path)
        finally:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            return
        except OSError:
            return
