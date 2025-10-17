from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import portalocker

BASE_DIR = Path(__file__).resolve().parent.parent
USERS_FILE = BASE_DIR / "users.json"
ORDERS_FILE = BASE_DIR / "orders.json"
GROUPS_FILE = BASE_DIR / "groups.json"
MENU_FILE = BASE_DIR / "menu.json"
PAYMENTS_FILE = BASE_DIR / "payments.json"


def _ensure_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if path.name in {"users.json", "groups.json"}:
            path.write_text("[]\n", encoding="utf-8")
        elif path.name in {"menu.json"}:
            path.write_text('{"drinks": [], "foods": []}\n', encoding="utf-8")
        else:
            path.write_text("{}\n", encoding="utf-8")


@contextmanager
def locked_file(path: Path) -> Iterator[Any]:
    """
    Blocca il file solo durante la scrittura, compatibile con Windows.
    """
    _ensure_file(path)
    with open(path, "r+", encoding="utf-8") as handle:
        portalocker.lock(handle, portalocker.LOCK_EX)
        try:
            yield handle
        finally:
            handle.flush()
            os.fsync(handle.fileno())
            portalocker.unlock(handle)


def read_json_file(path: Path) -> Any:
    """
    Lettura libera, senza lock: evita PermissionError e deadlock.
    """
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return None
    except OSError:
        return None


def write_json_file(path: Path, data: Any) -> bool:
    """
    Scrittura con lock esclusivo, sicura per accessi concorrenti.
    """
    try:
        _ensure_file(path)
        with locked_file(path) as handle:
            handle.seek(0)
            handle.truncate()
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return True
    except OSError as e:
        print(f"[storage] Errore scrittura {path}: {e}")
        return False
