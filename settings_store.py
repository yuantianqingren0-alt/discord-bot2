"""サーバーごとの設定(ON/OFF・招待リンク許可チャンネル)をJSONファイルに永続化する"""
import json
import os
from pathlib import Path

# Renderで永続ディスクをマウントする場合は環境変数 SETTINGS_DATA_DIR で指定
DATA_DIR = os.getenv(
    "SETTINGS_DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
)
DATA_FILE = os.path.join(DATA_DIR, "settings.json")

_store: dict = {}


def _load() -> None:
    global _store
    if not os.path.exists(DATA_FILE):
        _store = {}
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
            # JSON読み込み時にチャンネルID等を int 型に補正
            _store = {}
            for guild_id, data in loaded_data.items():
                _store[str(guild_id)] = {
                    "enabled": bool(data.get("enabled", False)),
                    "allowed_invite_channels": [
                        int(cid) for cid in data.get("allowed_invite_channels", [])
                    ],
                }
    except (json.JSONDecodeError, OSError) as err:
        print(f"settings.jsonの読み込みに失敗しました: {err}")
        _store = {}


def _save() -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        # 一時ファイルに書いてから置換することでファイル破損を防ぐ
        temp_file = f"{DATA_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(_store, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, DATA_FILE)
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
    s["enabled"] = bool(enabled)
    _save()
    return s


def allow_invite_channel(guild_id: int, channel_id: int) -> dict:
    s = get_guild_settings(guild_id)
    cid = int(channel_id)
    if cid not in s["allowed_invite_channels"]:
        s["allowed_invite_channels"].append(cid)
        _save()
    return s


def disallow_invite_channel(guild_id: int, channel_id: int) -> dict:
    s = get_guild_settings(guild_id)
    cid = int(channel_id)
    s["allowed_invite_channels"] = [
        c for c in s["allowed_invite_channels"] if c != cid
    ]
    _save()
    return s


def is_invite_allowed_in_channel(guild_id: int, channel_id: int) -> bool:
    s = get_guild_settings(guild_id)
    return int(channel_id) in s["allowed_invite_channels"]


# モジュール読み込み時に一度だけデータ読込
_load()
