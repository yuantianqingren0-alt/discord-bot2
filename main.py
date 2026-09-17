import os
import json
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

# ==========================================
# Render (Web Service) ポート開通用 Flask設定
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is live and running!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()


# ==========================================
# 設定データの管理 (settings.json との連携)
# ==========================================
SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(guild_settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"設定保存エラー: {e}")

guild_settings = load_settings()

def get_guild_setting(guild_id: int):
    gid = str(guild_id)
    if gid not in guild_settings:
        guild_settings[gid] = {
            "enabled": True,
            "mode": "strict",  # default: strict / gentle
            "log_channel_id": None,
            "allowed_invite_channels": []
        }
        save_settings()
    return guild_settings[gid]


# ==========================================
# Bot基本設定
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class AntiTrollBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("スラッシュコマンドを同期しました。")

bot = AntiTrollBot()
tree = bot.tree


# ==========================================
# 共通処理: 処理ログの送信機能
# ==========================================
async def send_action_log(guild: discord.Guild, title: str, user: discord.User, reason: str, color: discord.Color):
    settings = get_guild_setting(guild.id)
    log_channel_id = settings.get("log_channel_id")
    if not log_channel_id:
        return

    log_channel = guild.get_channel(log_channel_id)
    if not log_channel:
        return

    embed = discord.Embed(
        title=f"🛡️ モデレーションログ: {title}",
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="対象ユーザー / 実行者", value=f"{user.mention} (`{user.id}`)", inline=False)
    embed.add_field(name="詳細 / 理由", value=reason, inline=False)
    embed.set_footer(text=f"Guild ID: {guild.id}")

    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass


# ==========================================
# モデレーションパネル（解除・BANボタン）
# ==========================================
class ModerationPanelView(discord.ui.View):
    def __init__(self, target_member: discord.Member):
        super().__init__(timeout=None)
        self.target_member = target_member

    @discord.ui.button(label="タイムアウト解除", style=discord.ButtonStyle.green, custom_id="untimeout_btn")
    async def untimeout_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("❌ 権限がありません。", ephemeral=True)
            return

        try:
            await self.target_member.timeout(None, reason=f"{interaction.user} による手動解除")
            await interaction.response.send_message(f"✅ {self.target_member.mention} のタイムアウトを解除しました。")
            await send_action_log(
                guild=interaction.guild,
                title="タイムアウト解除",
                user=self.target_member,
                reason=f"実行者: {interaction.user.mention}",
                color=discord.Color.green()
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ 解除に失敗しました: {e}", ephemeral=True)

    @discord.ui.button(label="BAN（永久追放）", style=discord.ButtonStyle.danger, custom_id="ban_btn")
    async def ban_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ 権限がありません。", ephemeral=True)
            return

        try:
            await self.target_member.ban(reason=f"{interaction.user} による手動BAN")
            await interaction.response.send_message(f"🔨 {self.target_member.mention} をBANしました。")
            await send_action_log(
                guild=interaction.guild,
                title="BAN実行",
                user=self.target_member,
                reason=f"実行者: {interaction.user.mention}",
                color=discord.Color.red()
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ BANに失敗しました: {e}", ephemeral=True)


# ==========================================
# モデレーション実行処理 (タイムアウト+DM+現場設置)
# ==========================================
async def apply_moderation(message: discord.Message, reason: str):
    guild = message.guild
    member = message.author
    settings = get_guild_setting(guild.id)

    duration_minutes = 60 if settings.get("mode") == "strict" else 10
    until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

    try:
        await message.delete()
    except Exception:
        pass

    try:
        await member.timeout(until, reason=reason)
    except Exception as e:
        print(f"タイムアウト失敗: {e}")

    try:
        dm_embed = discord.Embed(
            title="⚠️ 自動モデレーション通知",
            description=f"**{guild.name}** にて利用規約違反が検知されたため、一時的にタイムアウト処理が行われました。",
            color=discord.Color.gold()
        )
        dm_embed.add_field(name="理由", value=reason, inline=False)
        dm_embed.add_field(name="解除予定時刻", value=f"<t:{int(until.timestamp())}:R>", inline=False)
        await member.send(embed=dm_embed)
    except Exception:
        pass

    panel_embed = discord.Embed(
        title="🛡️ 自動対処ログ・モデレーションパネル",
        description=f"{member.mention} による違反行為を検知し、タイムアウトを実施しました。",
        color=discord.Color.red()
    )
    panel_embed.add_field(name="理由", value=reason, inline=True)
    panel_embed.add_field(name="処罰時間", value=f"{duration_minutes} 分間", inline=True)
    
    view = ModerationPanelView(target_member=member)
    await message.channel.send(embed=panel_embed, view=view)

    await send_action_log(
        guild=guild,
        title="自動タイムアウト",
        user=member,
        reason=f"発生チャンネル: {message.channel.mention}\n理由: {reason}\n処罰: {duration_minutes}分タイムアウト",
        color=discord.Color.orange()
    )


# ==========================================
# イベント検知 (スパム・招待・レイド)
# ==========================================
user_message_history = {}
join_history = []

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    settings = get_guild_setting(message.guild.id)
    if not settings.get("enabled"):
        return

    if message.author.guild_permissions.administrator:
        return

    now = datetime.now(timezone.utc)

    # --- A. 招待リンクフィルター ---
    if "discord.gg/" in message.content or "discord.com/invite/" in message.content:
        allowed_channels = settings.get("allowed_invite_channels", [])
        if message.channel.id not in allowed_channels:
            await apply_moderation(message, "許可されていないチャンネルでのDiscord招待リンク送信")
            return

    # --- B. メンションスパム検知 (5人以上) ---
    if len(message.mentions) >= 5:
        await apply_moderation(message, "大量メンション（5人以上）によるスパム行為")
        return

    # --- C. 連投スパム検知 (3秒以内に4通) ---
    uid = message.author.id
    if uid not in user_message_history:
        user_message_history[uid] = []
    
    user_message_history[uid].append(now)
    user_message_history[uid] = [t for t in user_message_history[uid] if (now - t).total_seconds() <= 3]

    if len(user_message_history[uid]) >= 4:
        user_message_history[uid] = []
        await apply_moderation(message, "短時間での大量メッセージ連投スパム")
        return

    await bot.process_commands(message)


@bot.event
async def on_member_join(member: discord.Member):
    settings = get_guild_setting(member.guild.id)
    if not settings.get("enabled"):
        return

    now = datetime.now(timezone.utc)
    join_history.append(now)

    recent_joins = [t for t in join_history if (now - t).total_seconds() <= 10]
    if len(recent_joins) >= 10:
        try:
            await member.timeout(timedelta(hours=24), reason="自動レイド対策機能作動")
            await send_action_log(
                guild=member.guild,
                title="🚨 レイド対策発動",
                user=member,
                reason="10秒以内に10人以上の大量参加を検知したため、新規参加者を保護のため自動タイムアウトしました。",
                color=discord.Color.dark_red()
            )
        except Exception:
            pass


# ==========================================
# スラッシュコマンド群 (/antitroll)
# ==========================================
antitroll_group = app_commands.Group(name="antitroll", description="AntiTroll Botの設定コマンド")

@antitroll_group.command(name="toggle", description="Botの有効化/無効化を切り替えます")
@app_commands.checks.has_permissions(administrator=True)
async def toggle_cmd(interaction: discord.Interaction):
    s = get_guild_setting(interaction.guild_id)
    s["enabled"] = not s["enabled"]
    save_settings()
    status = "有効 🟢" if s["enabled"] else "無効 🔴"
    await interaction.response.send_message(f"AntiTroll 機能を **{status}** に変更しました。", ephemeral=True)

@antitroll_group.command(name="mode", description="動作モードを変更します")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(mode=[
    app_commands.Choice(name="厳格モード (60分タイムアウト)", value="strict"),
    app_commands.Choice(name="マイルドモード (10分タイムアウト)", value="gentle")
])
async def mode_cmd(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    s = get_guild_setting(interaction.guild_id)
    s["mode"] = mode.value
    save_settings()
    await interaction.response.send_message(f"動作モードを **{mode.name}** に設定しました。", ephemeral=True)

@antitroll_group.command(name="logset", description="対処ログを送信するチャンネルを設定/解除します")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="ログ宛先のテキストチャンネル（未指定で解除）")
async def logset_cmd(interaction: discord.Interaction, channel: discord.TextChannel = None):
    s = get_guild_setting(interaction.guild_id)
    if channel:
        s["log_channel_id"] = channel.id
        msg = f"対処ログの送信先を {channel.mention} に設定しました。"
    else:
        s["log_channel_id"] = None
        msg = "対処ログの送信先設定を解除しました。"
    save_settings()
    await interaction.response.send_message(f"✅ {msg}", ephemeral=True)

# ------------------------------------------
# 復元: 招待リンク許可チャンネル管理コマンド
# ------------------------------------------
@antitroll_group.command(name="allow_invite", description="指定したチャンネルでのDiscord招待リンク送信を許可します")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="許可するテキストチャンネル")
async def allow_invite_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    s = get_guild_setting(interaction.guild_id)
    allowed = s.setdefault("allowed_invite_channels", [])
    if channel.id not in allowed:
        allowed.append(channel.id)
        save_settings()
        await interaction.response.send_message(f"✅ {channel.mention} でのDiscord招待リンク送信を許可しました。", ephemeral=True)
    else:
        await interaction.response.send_message(f"ℹ️ {channel.mention} は既に許可されています。", ephemeral=True)

@antitroll_group.command(name="deny_invite", description="指定したチャンネルのDiscord招待リンク送信許可を解除します")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="許可を解除するテキストチャンネル")
async def deny_invite_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    s = get_guild_setting(interaction.guild_id)
    allowed = s.setdefault("allowed_invite_channels", [])
    if channel.id in allowed:
        allowed.remove(channel.id)
        save_settings()
        await interaction.response.send_message(f"✅ {channel.mention} の招待リンク許可を解除しました。", ephemeral=True)
    else:
        await interaction.response.send_message(f"ℹ️ {channel.mention} は許可リストに登録されていません。", ephemeral=True)

@antitroll_group.command(name="list_invites", description="招待リンクの送信が許可されているチャンネル一覧を表示します")
@app_commands.checks.has_permissions(administrator=True)
async def list_invites_cmd(interaction: discord.Interaction):
    s = get_guild_setting(interaction.guild_id)
    allowed_ids = s.get("allowed_invite_channels", [])
    if not allowed_ids:
        await interaction.response.send_message("ℹ️ 招待リンクが許可されているチャンネルはありません。（全テキストチャンネルで禁止中）", ephemeral=True)
        return

    mentions = [f"<#{cid}>" for cid in allowed_ids]
    embed = discord.Embed(
        title="🔗 招待リンク許可チャンネル一覧",
        description="\n".join(mentions),
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@antitroll_group.command(name="status", description="現在の設定状態を表示します")
@app_commands.checks.has_permissions(administrator=True)
async def status_cmd(interaction: discord.Interaction):
    s = get_guild_setting(interaction.guild_id)
    log_ch = f"<#{s['log_channel_id']}>" if s.get("log_channel_id") else "未設定"
    allowed_ids = s.get("allowed_invite_channels", [])
    allowed_str = f"{len(allowed_ids)} 個のチャンネル" if allowed_ids else "なし (全禁止)"
    
    embed = discord.Embed(title="🛡️ AntiTroll 設定ステータス", color=discord.Color.blue())
    embed.add_field(name="機能状態", value="有効 🟢" if s["enabled"] else "無効 🔴", inline=False)
    embed.add_field(name="動作モード", value="厳格 (60分)" if s["mode"] == "strict" else "マイルド (10分)", inline=False)
    embed.add_field(name="ログチャンネル", value=log_ch, inline=False)
    embed.add_field(name="招待リンク許可数", value=allowed_str, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

tree.add_command(antitroll_group)


# ==========================================
# 追加管理コマンド (/purge, /userinfo, /lockdown)
# ==========================================
@tree.command(name="purge", description="指定した数のメッセージを一括削除します")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(
    amount="削除するメッセージ数 (1~100)",
    target="特定のユーザーのメッセージのみ削除したい場合に指定"
)
async def purge_command(
    interaction: discord.Interaction, 
    amount: app_commands.Range[int, 1, 100], 
    target: discord.Member = None
):
    if not interaction.guild:
        await interaction.response.send_message("❌ このコマンドはサーバー内でのみ実行できます。", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    channel = interaction.channel

    def check(msg):
        if target:
            return msg.author.id == target.id
        return True

    try:
        deleted = await channel.purge(limit=amount, check=check)
        count = len(deleted)
        
        target_str = f" ({target.mention} のみ)" if target else ""
        await interaction.followup.send(f"🧹 {count} 件のメッセージを削除しました。{target_str}", ephemeral=True)
        
        await send_action_log(
            guild=interaction.guild,
            title="🧹 メッセージ一括削除",
            user=interaction.user,
            reason=f"{channel.mention} で {count} 件のメッセージを削除{target_str}",
            color=discord.Color.blue()
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ Botに「メッセージの管理」権限が付与されていません。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ 削除中にエラーが発生しました: {e}", ephemeral=True)


@tree.command(name="userinfo", description="指定したユーザーのアカウント・サーバー参加情報を表示します")
@app_commands.describe(target="情報を確認したいメンバー")
async def userinfo_command(interaction: discord.Interaction, target: discord.Member = None):
    if not interaction.guild:
        await interaction.response.send_message("❌ このコマンドはサーバー内でのみ実行できます。", ephemeral=True)
        return

    member = target or interaction.user
    now = datetime.now(timezone.utc)

    created_at = member.created_at
    created_days = (now - created_at).days
    
    joined_at = member.joined_at
    joined_days = (now - joined_at).days if joined_at else "不明"

    roles = [role.mention for role in member.roles if role != interaction.guild.default_role]
    roles_str = ", ".join(roles) if roles else "なし"

    warning_flag = "⚠️ **作成直後のアカウント (7日以内)**" if created_days <= 7 else "✅ 正常"

    embed = discord.Embed(
        title=f"👤 ユーザー情報: {member.display_name}",
        color=member.color if member.color != discord.Color.default() else discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ユーザー名 / ID", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="アカウント作成日", value=f"<t:{int(created_at.timestamp())}:F>\n({created_days} 日前)", inline=True)
    
    if joined_at:
        embed.add_field(name="サーバー参加日", value=f"<t:{int(joined_at.timestamp())}:F>\n({joined_days} 日前)", inline=True)
    
    embed.add_field(name="アカウント状態", value=warning_flag, inline=False)
    embed.add_field(name=f"保有ロール ({len(roles)})", value=roles_str, inline=False)
    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="lockdown", description="現在のチャンネル（またはサーバー全体）の発言権限を緊急ロック/解除します")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.describe(
    action="ロック（発言禁止）または 解除（発言許可）",
    scope="適用範囲（このチャンネルのみ / サーバー全体）"
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="🔒 ロックダウン実行", value="lock"),
        app_commands.Choice(name="🔓 ロックダウン解除", value="unlock")
    ],
    scope=[
        app_commands.Choice(name="このチャンネルのみ", value="channel"),
        app_commands.Choice(name="サーバー全体のテキストチャンネル", value="server")
    ]
)
async def lockdown_command(
    interaction: discord.Interaction, 
    action: app_commands.Choice[str], 
    scope: app_commands.Choice[str]
):
    if not interaction.guild:
        await interaction.response.send_message("❌ このコマンドはサーバー内でのみ実行できます。", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    is_lock = (action.value == "lock")
    send_messages_perm = False if is_lock else None

    target_channels = []
    if scope.value == "channel":
        target_channels.append(interaction.channel)
    else:
        target_channels = [ch for ch in interaction.guild.text_channels]

    updated_count = 0
    for ch in target_channels:
        try:
            overwrite = ch.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = send_messages_perm
            await ch.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            updated_count += 1
            
            try:
                if is_lock:
                    await ch.send("🔒 **このチャンネルは現在ロックダウンされています（発言権限停止中）。**")
                else:
                    await ch.send("🔓 **ロックダウンが解除されました。**")
            except Exception:
                pass
        except Exception:
            continue

    status_text = "ロックダウン（発言禁止）" if is_lock else "ロックダウン解除"
    await interaction.followup.send(f"✅ {updated_count} 個のチャンネルで `{status_text}` を実行しました。", ephemeral=True)

    await send_action_log(
        guild=interaction.guild,
        title=f"{'🔒' if is_lock else '🔓'} 緊急ロックダウン実行",
        user=interaction.user,
        reason=f"範囲: {scope.name} / 処理: {status_text}",
        color=discord.Color.red() if is_lock else discord.Color.green()
    )


# ==========================================
# 起動処理
# ==========================================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("エラー: DISCORD_TOKEN の環境変数が設定されていません。")
