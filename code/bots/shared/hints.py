from discord import Embed as _DiscordEmbed
from typing import (
    TypedDict,
    Optional,
    List,
    Literal,
    Union,
    NotRequired,
    Dict
)



class ChannelDict(TypedDict):
    name: List[str]
    topic: List[str]
    nsfw: List[bool]
    slowmode_delay: List[int]


class WebhookDict(TypedDict):
    name: List[str]
    

class RoleDict(TypedDict):
    name: List[str]
    permissions: List[int]
    color: List[str]
    hoist: List[bool]
    mentionable: List[bool]


class EmojiDict(TypedDict):
    name: List[str]
    image: List[str]


class StickerDict(TypedDict):
    name: List[str]
    description: List[str]
    emoji: List[str]
    image: List[str]


class _EmbedFooter(TypedDict):
    text: str
    icon_url: Optional[str]


class _EmbedAuthor(TypedDict):
    name: str
    url: Optional[str]
    icon_url: Optional[str]


class _EmbedField(TypedDict):
    name: str
    value: str
    inline: bool


class EmbedDict(TypedDict):
    title: str
    description: str
    color: int
    footer: NotRequired[_EmbedFooter]
    thumbnail: NotRequired[str]
    author: NotRequired[_EmbedAuthor]
    image: Optional[str]
    fields: NotRequired[List[_EmbedField]]


class MessageDict(TypedDict):
    content: List[str]
    tts: List[bool]
    embed: List[Union[EmbedDict, _DiscordEmbed, None]]
    username: List[str]
    avatar_url: List[str]


class PrefixDict(TypedDict):
    prefixes: List[str]


class MemberDict(TypedDict):
    nick: List[str]
    mute: List[bool]
    deafen: List[bool]
    supress: List[bool]
    timed_out_until: List[int]


class GuildDict(TypedDict):
    name: List[str]
    icon: List[str]


class SettingsData(TypedDict):
    reasons: List[str]
    prefixes: List[str]
    webhook_amount: Literal[26, 46]
    channel: ChannelDict
    webhook: WebhookDict
    role: RoleDict
    emoji: EmojiDict
    sticker: StickerDict
    member: MemberDict
    guild: GuildDict
    message: MessageDict


class CookieData(TypedDict):
    id: int
    name: str
    avatar: str

    
class TAuthData(TypedDict):
    id: int
    username: str
    avatar: Optional[str]
    access_token: str
    token_type: str
    expires: int
    refresh_token: str
    scope: str
    email: str



class UserData(TypedDict):
    id: int
    is_premium: bool
    is_admin: bool
    is_owner: bool
    is_blacklisted: bool
    user_amount: int
    server_amount: int
    partners: List[int]
    settings: SettingsData
    auth_data: TAuthData


class PartialUserDict(TypedDict):
    id: int
    is_premium: bool
    is_admin: bool
    is_owner: bool
    is_blacklisted: bool
    user_amount: int
    server_amount: int
    partners: bytes
    settings: bytes
    auth_data: Optional[TAuthData]


class OverwriteBackup(TypedDict):
    member: Optional[int]
    role: Optional[int]
    overwrites: Dict[str, bool]


class EmojiBackup(TypedDict):
    id: Optional[int]
    name: Optional[str]
    url: Optional[str]
    # Discord keeps emojis in the order they were created.
    # Knowing the creation time of each emoji allows to recostruct
    # their original position
    created_at: Optional[float]
    unicode: Optional[str]


class StickerBackup(TypedDict):
    name: str
    description: str
    # Same as EmojiBackup.created_at
    created_at: int
    url: str


class MessagableBackup(TypedDict):
    id: int
    name: str
    nsfw: bool
    position: str
    category_id: Optional[int]
    slowmode_delay: int
    permissions_synced: bool
    overwrites: List[OverwriteBackup]


class TextChannelBackup(MessagableBackup):
    topic: Optional[str]
    news: bool
    default_auto_archive_duration: int


class VoiceChannelBackup(MessagableBackup):
    bitrate: int
    rtc_region: Optional[str]
    video_quality_mode: int
    user_limit: int


class ForumChannelTagBackup(TypedDict):
    name: str
    moderatred: bool
    emoji: Optional[EmojiBackup]


class ForumChannelBackup(MessagableBackup):
    topic: Optional[str]
    available_tags: List[ForumChannelTagBackup]
    default_layout: int
    default_sort_order: int
    default_reaction_emoji: Optional[EmojiBackup]
    default_thread_slowmode_delay: int
    default_auto_archive_duration: int


class StageChannelBackup(VoiceChannelBackup):
    topic: str


class CategoryBackup(TypedDict):
    name: str
    position: int
    overwrites: List[OverwriteBackup]


class ScheduledEventBackup(TypedDict):
    name: str
    description: Optional[str]
    channel_id: int
    location: Optional[str]
    entitiy_type: int
    privacy_level: int
    end_time: Optional[float]
    start_time: float
    cover_image: Optional[str]
    status: int


class RoleBackup(TypedDict):
    id: int
    name: str
    icon: Optional[str]
    color: int
    hoist: bool
    mentionable: bool
    bot_id: Optional[int]
    default: bool
    position: str
    permissions: int


class MemberBackup(TypedDict):
    id: int
    nick: Optional[str]
    roles: List[int]
    timed_out_until: Optional[float]


class AutoModTriggerBackup(TypedDict):
    type: int
    presets: Optional[int]
    keyword_filter: Optional[List[str]]
    allow_list: Optional[List[str]]
    mention_limit: Optional[int]
    regex_patterns: Optional[List[str]]
    mention_raid_protection: Optional[bool]


class AutoModActionBackup(TypedDict):
    type: Optional[int]
    duration: Optional[float]
    channel_id: Optional[int]
    custom_message: Optional[str]


class AutoModRuleBackup(TypedDict):
    name: str
    event_type: int
    trigger: AutoModTriggerBackup
    actions: List[AutoModActionBackup]
    enabled: bool
    exempt_role_ids: List[int]
    exempt_channel_ids: List[int]


class SoundboardSoundBackup(TypedDict):
    name: str
    available: bool
    volume: float
    emoji: EmojiBackup
    sound: str


class GuildBackup(TypedDict):
    name: str
    icon: Optional[str]
    banner: Optional[str]
    community: bool
    description: Optional[str]
    vanity_code: str
    preferred_locale: str
    premium_progress_bar_enabled: int
    afk_timeout: int
    afk_channel_id: Optional[int]
    rules_channel_id: Optional[int]
    public_updates_channel_id: Optional[int]
    system_channel_id: Optional[int]
    system_channel_flags: int
    invites_paused_until: Optional[int]
    dms_paused_until: Optional[int]
    default_notification: int
    verification_level: int
    explicit_content_filter: int
    splash: Optional[str]
    discovery_splash: Optional[str]
    discoverable: bool
    widget_enabled: bool
    widget_channel_id: Optional[int]


class BackupData(TypedDict):
    members: List[MemberBackup]
    roles: List[RoleBackup]
    text_channels: List[TextChannelBackup]
    voice_channels: List[VoiceChannelBackup]
    stage_channels: List[StageChannelBackup]
    forum_channels: List[ForumChannelBackup]
    categories: List[CategoryBackup]
    soundboard_sounds: List[SoundboardSoundBackup]
    scheduled_events: List[ScheduledEventBackup]
    automod_rules: List[AutoModRuleBackup]
    emojis: List[EmojiBackup]
    stickers: List[StickerBackup]
    guild: GuildBackup


class TBlocked(TypedDict):
    user_id: int
    reason: str
    expires: float
    system: bool
    expired: bool