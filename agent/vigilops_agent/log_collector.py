"""Log collection: tail-f, metadata, multiline merge, offset persistence, Docker json-log."""
import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from vigilops_agent.config import LogSourceConfig

logger = logging.getLogger(__name__)

OFFSET_FILE = os.path.expanduser("~/.vigilops/offsets.json")
LEVEL_RE = re.compile(r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b", re.IGNORECASE)
LEVEL_MAP = {"WARNING": "WARN", "CRITICAL": "FATAL"}


def _detect_level(line: str) -> str:
    m = LEVEL_RE.search(line)
    if m:
        lvl = m.group(1).upper()
        return LEVEL_MAP.get(lvl, lvl)
    return "INFO"


def load_offsets() -> Dict[str, int]:
    try:
        with open(OFFSET_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_offsets(offsets: Dict[str, int]) -> None:
    p = Path(OFFSET_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(offsets, f)


class LogTailer:
    """Async tail -f for a single log file."""

    def __init__(
        self,
        source: LogSourceConfig,
        host_id: int,
        callback: Callable,
        offsets: Dict[str, int],
    ):
        self.source = source
        self.host_id = host_id
        self.callback = callback
        self.offsets = offsets
        self._pending: Optional[Dict] = None  # for multiline merge
        self._pending_time: float = 0.0

    def _parse_docker_json(self, raw: str) -> Optional[str]:
        """Parse Docker json-log format, return the actual log line."""
        try:
            obj = json.loads(raw)
            return obj.get("log", "").rstrip("\n")
        except (json.JSONDecodeError, AttributeError):
            return raw.rstrip("\n")

    def _make_entry(self, message: str) -> Dict:
        return {
            "host_id": self.host_id,
            "service": self.source.service,
            "source": self.source.path,
            "level": _detect_level(message),
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _flush_pending(self) -> None:
        if self._pending:
            await self.callback(self._pending)
            self._pending = None

    async def _process_line(self, line: str) -> None:
        if self.source.docker:
            line = self._parse_docker_json(line) or ""
            if not line:
                return

        if not self.source.multiline:
            await self.callback(self._make_entry(line))
            return

        # Multiline merge
        is_start = bool(re.match(self.source.multiline_pattern, line))
        if is_start:
            await self._flush_pending()
            self._pending = self._make_entry(line)
            self._pending_time = time.monotonic()
        else:
            if self._pending:
                self._pending["message"] += "\n" + line
            else:
                # No pending, treat as standalone
                await self.callback(self._make_entry(line))

    async def run(self) -> None:
        path = self.source.path
        if not os.path.exists(path):
            logger.warning(f"Log file not found: {path}")
            return

        offset = self.offsets.get(path, None)
        try:
            f = open(path, "r", errors="replace")
        except OSError as e:
            logger.warning(f"Cannot open {path}: {e}")
            return

        try:
            if offset is not None:
                f.seek(offset)
            else:
                f.seek(0, 2)  # seek to end

            logger.info(f"Tailing {path} from offset {f.tell()}")
            while True:
                line = f.readline()
                if line:
                    line = line.rstrip("\n")
                    if line:
                        await self._process_line(line)
                    self.offsets[path] = f.tell()
                else:
                    # No new data — check multiline timeout
                    if self._pending and (time.monotonic() - self._pending_time) > 2.0:
                        await self._flush_pending()
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            await self._flush_pending()
            raise
        finally:
            f.close()


class LogCollector:
    """Manages all log tailers and batches entries for upload."""

    def __init__(self, host_id: int, sources: List[LogSourceConfig], report_fn: Callable):
        self.host_id = host_id
        self.sources = sources
        self.report_fn = report_fn  # async fn(logs: list) -> bool
        self.offsets = load_offsets()
        self._buffer: List[Dict] = []
        self._lock = asyncio.Lock()
        self._tasks: List[asyncio.Task] = []

    async def _on_log_entry(self, entry: Dict) -> None:
        async with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= 100:
                await self._flush()

    async def _flush(self) -> None:
        """Flush buffer (caller holds lock)."""
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        success = await self.report_fn(batch)
        if success:
            save_offsets(self.offsets)

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(5)
            async with self._lock:
                await self._flush()

    async def start(self) -> List[asyncio.Task]:
        tasks = []
        for src in self.sources:
            tailer = LogTailer(src, self.host_id, self._on_log_entry, self.offsets)
            tasks.append(asyncio.create_task(tailer.run()))
        tasks.append(asyncio.create_task(self._flush_loop()))
        self._tasks = tasks
        logger.info(f"Log collector started: {len(self.sources)} sources")
        return tasks
