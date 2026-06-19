import json
import logging
import shutil
from datetime import date, datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "stores.json"

_DEFAULT = {"stores": {}, "last_heartbeat": 0}

logger = logging.getLogger(__name__)


def _load() -> dict:
    if not DATA_FILE.exists():
        return _DEFAULT.copy()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if "stores" not in data:
            data["stores"] = {}
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Corrupted stores.json: {e} — backing up and resetting")
        backup = DATA_FILE.with_suffix(f".backup_{int(datetime.now().timestamp())}.json")
        shutil.copy2(DATA_FILE, backup)
        return _DEFAULT.copy()


def _save(data: dict) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Stores ────────────────────────────────────────────────────────────────────

def all_stores() -> dict:
    return _load()["stores"]


def get_store(store_id: str) -> dict | None:
    return _load()["stores"].get(store_id)


def add_store(name: str, url: str, cookie: str, interval_minutes: int = 20) -> str:
    data = _load()
    store_id = str(int(datetime.now().timestamp()))
    handle = url.lstrip("@").strip("/")
    data["stores"][store_id] = {
        "name": name,
        "url": f"https://www.enjoei.com.br/@{handle}",
        "cookie": cookie,
        "interval_minutes": interval_minutes,
        "next_run": 0,
        "active": True,
        "stats": {},
        "last_boost": None,
        "added_at": datetime.now().isoformat(),
        "consecutive_errors": 0,
    }
    _save(data)
    return store_id


def rename_store(store_id: str, new_name: str) -> None:
    data = _load()
    if store_id in data["stores"]:
        data["stores"][store_id]["name"] = new_name
        _save(data)


def remove_store(store_id: str) -> None:
    data = _load()
    data["stores"].pop(store_id, None)
    _save(data)


def set_store_interval(store_id: str, minutes: int) -> None:
    data = _load()
    if store_id in data["stores"]:
        data["stores"][store_id]["interval_minutes"] = minutes
        data["stores"][store_id]["next_run"] = 0
        _save(data)


def set_next_run(store_id: str, timestamp: float) -> None:
    data = _load()
    if store_id in data["stores"]:
        data["stores"][store_id]["next_run"] = timestamp
        _save(data)


def record_boost(store_id: str, count: int) -> None:
    data = _load()
    store = data["stores"].get(store_id)
    if not store:
        return
    today = date.today().isoformat()
    if today not in store["stats"]:
        store["stats"][today] = {"total_boosts": 0, "rounds": 0}
    store["stats"][today]["total_boosts"] += count
    store["stats"][today]["rounds"] += 1
    store["last_boost"] = datetime.now().isoformat()
    store["consecutive_errors"] = 0
    _save(data)


def today_stats(store_id: str) -> dict:
    store = _load()["stores"].get(store_id, {})
    today = date.today().isoformat()
    return store.get("stats", {}).get(today, {"total_boosts": 0, "rounds": 0})


# ── Error tracking ───────────────────────────────────────────────────────────

def increment_errors(store_id: str) -> int:
    data = _load()
    store = data["stores"].get(store_id)
    if not store:
        return 0
    store["consecutive_errors"] = store.get("consecutive_errors", 0) + 1
    _save(data)
    return store["consecutive_errors"]


def reset_errors(store_id: str) -> None:
    data = _load()
    store = data["stores"].get(store_id)
    if not store:
        return
    store["consecutive_errors"] = 0
    _save(data)


def deactivate_store(store_id: str) -> None:
    data = _load()
    store = data["stores"].get(store_id)
    if store:
        store["active"] = False
        _save(data)


def activate_store(store_id: str) -> None:
    data = _load()
    store = data["stores"].get(store_id)
    if store:
        store["active"] = True
        _save(data)


# ── Heartbeat ────────────────────────────────────────────────────────────────

def update_heartbeat() -> None:
    data = _load()
    data["last_heartbeat"] = datetime.now().isoformat()
    _save(data)


def get_heartbeat() -> str | None:
    data = _load()
    return data.get("last_heartbeat")


# ── Kick / reset ─────────────────────────────────────────────────────────────

def kick_all_stores() -> list[str]:
    """Reset all stores: reactivate, clear errors, set next_run=0. Returns names of reset stores."""
    data = _load()
    names = []
    for sid, store in data["stores"].items():
        store["active"] = True
        store["consecutive_errors"] = 0
        store["next_run"] = 0
        names.append(store["name"])
    _save(data)
    return names
