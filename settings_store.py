"""サーバーごとの設定(ON/OFF・招待リンク許可チャンネル)をJSONファイルに永続化する"""
import json
import os

# Renderで永続ディスクをマウントする場合は環境変数 SETTINGS_DATA_DIR で
# マウント先(例: /data)を指定してください。未指定時はこのファイルと同じ場所に保存します。
DATA_DIR = os.getenv(
    "SETTINGS_DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
)
DATA_FILE = os.path.join(DATA_DIR, "settings.json")

_store: dict = {}


def _ensure_file() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("{}")


def _load() -> None:
    global _store
    _ensure_file()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            _store = json.load(f) or {}
    except (json.JSONDecodeError, OSError) as err:
        print(f"settings.jsonの読み込みに失敗しました: {err}")
        _store = {}


def _save() -> None:
    _ensure_file()
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_store, f, ensure_ascii=False, indent=2)
    except OSError as err:
        print(f"settings.jsonの保存に失敗しました: {err}")


def get_guild_settings(guild_id: int) -> dict:
    key = str(guild_id)
    if key not in _store:
        _store[key] = {"enabled": False, "allowed_invite_channels": []}
        _save()
    return _store[key]


def is_enabled(guild_id: int) -> bool:
    return get_guild_settings(guild_id).get("enabled") is True


def set_enabled(guild_id: int, enabled: bool) -> dict:
    s = get_guild_settings(guild_id)
    s["enabled"] = enabled
    _save()
    return s


def allow_invite_channel(guild_id: int, channel_id: int) -> dict:
    s = get_guild_settings(guild_id)
    if channel_id not in s["allowed_invite_channels"]:
        s["allowed_invite_channels"].append(channel_id)
        _save()
    return s


def disallow_invite_channel(guild_id: int, channel_id: int) -> dict:
    s = get_guild_settings(guild_id)
    s["allowed_invite_channels"] = [
        c for c in s["allowed_invite_channels"] if c != channel_id
    ]
    _save()
    return s


def is_invite_allowed_in_channel(guild_id: int, channel_id: int) -> bool:
    s = get_guild_settings(guild_id)
    return channel_id in s["allowed_invite_channels"]


_load()
