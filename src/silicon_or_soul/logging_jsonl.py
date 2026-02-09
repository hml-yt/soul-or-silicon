from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config


class RoundLogger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config.LOGS_DIR / "game_log.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_round(self, payload: dict[str, Any]) -> None:
        payload = dict(payload)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

