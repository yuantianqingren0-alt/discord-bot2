# 荒らし対策の閾値・動作設定

SPAM = {
    "enabled": True,
    "max_messages": 5,        # 6秒間に5個以上のメッセージで検知
    "interval_ms": 6000,      # 6000ミリ秒 = 6秒間
    "duplicate_threshold": 5, # 同じ文面が5回連続したら検知
    "timeout_ms": 300000,     # 5分間タイムアウト (300,000ms)
    "delete_messages": True,  # 該当メッセージを自動削除
}

MENTION_SPAM = {
    "enabled": True,
    "max_mentions": 5,        # 1メッセージ内メンション5個以上で検知
    "timeout_ms": 600000,     # 10分間タイムアウト (600,000ms)
}

INVITE_FILTER = {
    "enabled": True,
}

ANTI_RAID = {
    "enabled": True,
    "join_interval_ms": 10000, # 10秒間
    "join_threshold": 5,       # 5人参加でレイド判定
    "lockdown_ms": 600000,     # 10分間ロックダウン
    "action": "quarantine",    # "quarantine" (隔離ロール付与) または "kick"
}

WHITELIST = {
    "exempt_admins": True,     # 管理者権限を持つユーザーを除外するか
    "exempt_role_ids": [],     # 除外したいロールIDのリスト (例: [123456789012345678])
}
