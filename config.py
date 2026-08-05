"""
荒らし対策Bot 設定ファイル
数値やON/OFFは自由に調整してください(時間はすべてミリ秒 [ms])
"""

# --- スパム(連投)検知 ---
SPAM = {
    "enabled": True,
    "max_messages": 5,          # この件数を超えたら発動
    "interval_ms": 5000,        # この時間内(ms)にmax_messagesを超えると検知
    "duplicate_threshold": 3,   # 同一内容を連続でこの回数投稿したら検知
    "timeout_ms": 10 * 60 * 1000,  # 検知時のタイムアウト時間(10分)
    "delete_messages": True,    # 検知したメッセージを削除するか
}

# --- メンション荒らし対策 ---
MENTION_SPAM = {
    "enabled": True,
    "max_mentions": 5,             # 1メッセージ内の最大メンション数
    "timeout_ms": 15 * 60 * 1000,  # 15分タイムアウト
}

# --- 招待リンクフィルター ---
# 招待リンクはデフォルトで全チャンネル禁止です。
# 特定チャンネルのみ許可したい場合は /antitroll invite allow コマンドで設定してください。
# (許可リストは data/settings.json に保存され、ここでは編集しません)
INVITE_FILTER = {
    "enabled": True,
}

# --- 大量参加(レイド)検知 ---
ANTI_RAID = {
    "enabled": True,
    "join_threshold": 6,             # この人数が
    "join_interval_ms": 10000,       # この時間内(ms)に参加したらレイドとみなす
    "action": "quarantine",          # "quarantine"(隔離ロール付与) or "kick"
    "lockdown_ms": 5 * 60 * 1000,    # レイド検知後、新規参加者を自動処理する期間
}

# --- 除外設定 ---
WHITELIST = {
    "exempt_admins": True,   # 管理者権限(Administrator)を持つユーザーは常に除外
    "exempt_role_ids": [],   # 除外するロールID(モデレーターなど)
}
