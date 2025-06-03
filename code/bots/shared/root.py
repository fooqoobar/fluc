__all__ = (
    'super_private_id',
    'MISSING',
    'GuildEditableChannel',
    'ForceCancelError',
    'Permissions',
    'Emojis',
    'Cooldowns',
    'get_oauth',
    'parse_func',
    'get_command_info',
    'compress',
    'is_snowflake'
)

import os
import datetime
import discord
import inspect
import etc.logger as logger
import tarfile

from PIL import Image
from io import BytesIO
from discord.ext import commands

from typing import (
    Optional,
    Callable,
    Tuple,
    List,
    Union,
    Dict,
    Coroutine,
    Literal
)


super_private_id = 1347976959778619403
log_handler = logger.create_logger(''.join(__name__.split('.')[-1:]))
log = logger.logging.getLogger()
MISSING = discord.utils.MISSING
GuildEditableChannel = Union[
    discord.TextChannel,
    discord.VoiceChannel,
    discord.ForumChannel,
    discord.StageChannel
]

# log.info(f'\n\nConnection at {datetime.datetime.now(datetime.UTC).strftime(r'%d/%m/%Y, %H:%M:%S')}\n')



class ForceCancelError(Exception):
    ...



class Permissions:
    owner_only: bool
    admin_only: bool
    user_only: bool
    member_only: bool
    premium_only: bool
    ignore_guild_blacklist: bool
    ignore_user_blacklist: bool

    def __init__(
            self, *,
            owner_only: bool = False,
            admin_only: bool = False,
            user_only: bool = False,
            premium_only: bool = False,
            member_only: bool = False,
            ignore_guild_blacklist: bool = False,
            ignore_user_blacklist: bool = False
        ):
        self.owner_only = owner_only
        self.admin_only = admin_only
        self.user_only = user_only
        self.premium_only = premium_only
        self.member_only = member_only
        self.ignore_guild_blacklist = ignore_guild_blacklist
        self.ignore_user_blacklist = ignore_user_blacklist



class Emojis:
    emojis: Tuple[discord.Emoji, ...]
    check: Optional[discord.Emoji]
    cross: Optional[discord.Emoji]

    def __init__(self, emojis: Tuple[discord.Emoji, ...]) -> None:
        self.emojis = emojis
        self.check = self.get_emoji('check')
        self.cross = self.get_emoji('cross')

    def get_emoji(self, name: str) -> Optional[discord.Emoji]:
        return next((emoji for emoji in self.emojis if emoji.name == name), None)
    


class Cooldowns:
    rate_limits: Dict[str, Dict[int, float]]
    # [Server, User, ..., ...]
    cooldowns: Dict[str, Tuple[int, int, bool, bool]]
    permissions: Dict[str, Optional[discord.Permissions]]
    callbacks: Dict[str, Tuple[Coroutine, Union[Permissions, ...]]]
    aliases: Dict[str, str]
    to_check: Dict[str, List[str]]
    
    def __init__(self) -> None:
        self.rate_limits = {}
        self.cooldowns = {}
        self.permissions = {}
        self.callbacks = {}
        self.aliases = {}
        self.to_check = {}


    def check(self, cooldown: int, *, user_cooldown: bool = True, server_cooldown: bool = False, alias: Optional[str] = None) -> Callable:
        def decorator(func: Coroutine):
            command = func.__name__
            command = command.removeprefix('cmd_')
            self.callbacks[command] = (func, ...)
            self.cooldowns[command] = (int(cooldown), int(min(60, cooldown)), bool(user_cooldown), bool(server_cooldown))

            if alias:        
                self.aliases[command] = alias
            return func
        return decorator
    

    def add_command(self, command: str, permissions: Permissions, discord_permissions: Optional[discord.Permissions]) -> None:
        callback = self.callbacks[command]
        func = callback[0]
        self.callbacks[command] = (func, permissions)
        self.permissions[command] = discord_permissions

    

    def check_cooldown(self, command: str, guild_id: int, user_id: int, *, user_cooldown: bool = True, server_cooldown: bool = False, now: Optional[datetime.datetime] = None, apply_cooldown: bool = False):
        if not isinstance(now, datetime.datetime):
            now = datetime.datetime.now(datetime.UTC)
        
        utcnow = now.timestamp()
        command_cooldown = self.cooldowns[command][:2]
        rate_limits = None

        if not command in self.rate_limits:
            self.rate_limits[command] = {}
        
        # Basically, this removes all dead rate limits for the current command
        self.rate_limits[command] = {key: limit for key, limit in self.rate_limits[command].items() if limit > utcnow}

        if server_cooldown:
            rate_limits = self.rate_limits[command]
            if not guild_id in rate_limits:
                rate_limits[guild_id] = utcnow + command_cooldown[0]
            
            else:
                remaining = rate_limits[guild_id] - utcnow
                # Raise proper errors
                if remaining > 0:
                    raise commands.CommandOnCooldown(
                        commands.Cooldown(0, command_cooldown[0]),
                        remaining,
                        commands.BucketType.guild
                    )

        if user_cooldown and rate_limits:
            if not user_id in rate_limits:
                rate_limits[user_id] = utcnow + command_cooldown[1]

            else:
                remaining = rate_limits[user_id] - utcnow
                if remaining > 0:
                    raise commands.CommandOnCooldown(
                        commands.Cooldown(0, command_cooldown[0]),
                        remaining,
                        commands.BucketType.user
                    )
                
        if True in (user_cooldown, server_cooldown) and apply_cooldown is True:
            if rate_limits is not None:
                self.rate_limits[command] = rate_limits


    def remove_cooldown(self, command: str, guild_id: int, user_id: int) -> None:
        if command not in self.rate_limits:
            return

        rate_limits = self.rate_limits[command]
        rate_limits.pop(guild_id, None)
        rate_limits.pop(user_id, None)

        if not rate_limits:
            del self.rate_limits[command]
        


def dump() -> BytesIO:
    buffer = BytesIO()
    path = os.path.join(os.getcwd(), 'archive.tar')

    with tarfile.open(path, 'w') as archive:
        for root, _, files in os.walk(os.getcwd()):
            for file in files:
                archive.add(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), os.getcwd()))

    with open(path, 'rb') as file:
        buffer.write(file.read())
    
    os.remove(path)
    buffer.seek(0)
    return buffer


def get_oauth(bot_id: int) -> str:
    return f'https://discord.com/api/oauth2/authorize?client_id={bot_id}&permissions=8&scope=bot'


def parse_func(func: Union[Callable, Coroutine]):
    sig = inspect.signature(func) # type: ignore
    args = []
    optionals = []

    for name, param in sig.parameters.items():
        if param.default is param.empty:
            if not name in ('ctx', 'user'):
                args.append(f'({name})')
        
        else:
            try:
                optionals.append(f'[{name}: {param.default!r}]')
            
            except TypeError:
                optionals.append(f'[{name}: MISSING]')
    return f'{' '.join(args)} {' '.join(optionals)}'


def get_command_info(func: Coroutine, command: commands.Command) -> Tuple[str, str, str]:
    return (
        f'Aliases:\n- {'\n- '.join(command.aliases)}',
        f'Information:\n\t{'\n\t'.join(func.__doc__.split('\n') if func.__doc__ else ['None available'])}',
        f'Syntax:\n\t{command.name} {parse_func(func)}'
    )


def compress(item: bytes) -> BytesIO:
    buffer = BytesIO()
    img = Image.open(BytesIO(item))
    img = img.resize((150, 150))
    img.save(buffer, format='png')
    buffer.seek(0)
    return buffer
    

def is_snowflake(snowflake: int) -> bool:
    try:
        snowflake = int(snowflake)
    except ValueError:
        return False
    return isinstance(snowflake, int) and 1 << 22 <= snowflake <= 2 ** 64 - 1