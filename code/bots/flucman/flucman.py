#pyright: reportOptionalMemberAccess=false
#pyright: reportAttributeAccessIssue=false
#pyright: reportArgumentType=false

import discord
import aiohttp
import asyncio

from etc.logger import create_logger, Formatter
# from exchange.client import Client
# from exchange.server import Server
from etc.xorshift32 import XorShift32
from bots.shared import ext

from bots.shared.root import *
from bots.shared.commands import *
from bots.shared.hints import *
from bots.shared.ext import *
from bots.shared.ui import *
from bots.shared.aliases import *
from etc.database import *

from traceback import format_exc, format_exception
from logging import getLogger, ERROR as L_ERROR
from discord.ext import commands

from functools import partial
from typing import Optional


manager = commands.Bot(
    command_prefix=get_prefix,
    intents=discord.Intents.all(),
    help_command=None
)
database = Database()
database.connect()
# server = Server()
# database = server.database
# client = Client(database=database)
create_logger(__name__)
log = getLogger()
xorshift32 = XorShift32()
cooldowns = Cooldowns()
emojis: Optional[Emojis] = None
session: Optional[aiohttp.ClientSession] = None
ext.cooldowns = cooldowns
database.base_connect()




@manager.event
async def on_ready():
    global emojis
    global session

    log.info(f'Authorization link: {get_oauth(manager.user.id)}')

    session = manager.http._HTTPClient__session # type: ignore
    guild = manager.get_guild(database.config.emoji_guild)
    
    if guild is None:
        log.critical('Emoji guild not found.')
        await manager.close()
        return

    emojis = Emojis(guild.emojis)

    _ext_init = partial(
        ext_init,
        database,
        xorshift32,
        cooldowns,
        manager,
        session,
        emojis,
        manager=True
    )

    _ext_init()
    ui_init(
        database,
        session,
        cooldowns,
        manager,
        emojis
    )

    await add_commands(
        manager,
        database,
        cooldowns,
        _ext_init
    )

    manager.add_view(HelpMenu([cmd for cmd in manager.commands if not cmd.hidden]))
    manager.add_view(ManagerHelpMenu([cmd for cmd in manager.commands if cmd.hidden]))
    manager.add_view(Leaderboard())
    manager.add_view(InviteButton())
    manager.add_view(InviteButtonRedirect())
    log.info(f'Logged on {manager.user}')


@manager.event
async def on_member_join(member: discord.Member):
    role = discord.utils.get(member.guild.roles, name='@com')
    now = datetime.datetime.now(datetime.UTC)

    # Account has to be at least 1 week old
    if member.created_at and now.timestamp() + 60 * 60 * 24 * 7 > member.created_at.timestamp():
        try:
            await member.send(content='You can not join the server at this moment.')
        except discord.Forbidden:
            pass
        await member.kick(reason='Account kicked due to being too new.')
    await member.edit(nick=f'{member.global_name[:23]} #FLUC') # type: ignore

    try:
        def update_check(before: discord.Member, after: discord.Member):
            return after == member and role in after.roles
        
        await manager.wait_for('member_update', check=update_check, timeout=3600)
    except asyncio.TimeoutError:
        # Automatically kick the member after 1 hour if they haven't verified
        await member.kick(reason='Not verified')


@manager.event
async def on_member_uppdate(before: discord.Member, after: discord.Member):
    channel = discord.utils.get(after.guild.channels, name='，rich')
    roles = []
    for name in ['premium', 'premium boost']:
        role = discord.utils.get(after.guild.roles, name=name)
        if role:
            roles.append(role)

    for role in roles:
        if not role in before.roles and role in after.roles:
            user = database.get_user(after.id)
            if not user:
                user = User.new_user(after.id)
            user.is_premium = True
            database.update_user(user)
            await channel.send(embed=embed(title='Premium Added', description=f'Premium added. You are now rich {after.mention} ❤️'))
            break

        elif role in before.roles and not role in after.roles:
            user = database.get_user(after.id)
            user.is_premium = False
            database.update_user(user)
            await channel.send(embed=embed(title='Premium Removed', description=f'Premium removed. You are now poor {after.mention}'))
            break

    if not after.nick.endswith(' #FLUC'):
        await after.edit(nick=f'{after.global_name[:23]} #FLUC') # type: ignore


@manager.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    guild = manager.get_guild(payload.guild_id)
    verification_channel = discord.utils.get(guild.channels, name='auth')
    message = await get_from_iterator(verification_channel.history(limit=1, oldest_first=True))

    if payload.message_id == message.id:
        if payload.emoji == '✅':
            member = guild.get_member(payload.message_author_id)
            role = discord.utils.get(guild.roles, name='@com')
            if not role in member.roles:
                await member.add_roles(role)


@manager.event
async def on_command_error(ctx: commands.Context, error: discord.DiscordException):
    if (
        'AssertionError' in str(error) or
        isinstance(error, (commands.CommandNotFound))
    ):
        return
    
    elif isinstance(error, commands.CommandOnCooldown):
        now = datetime.datetime.now(datetime.UTC).timestamp()
        await ctx.channel.send(embed=discord.Embed(
            title='Error',
            description=f'{'This server is' if error.type == commands.BucketType.guild else 'You are'} on cooldown. Retry <t:{int(now - error.retry_after)}:R>'
        ), delete_after=error.retry_after)
    
    elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
        callback = cooldowns.callbacks[ctx.command.name]
        info = get_command_info(callback[0], ctx.command)
        err: str

        if isinstance(error, commands.MissingRequiredArgument):
            err = f'Missing required "{error.param.name}"'
        
        else:
            args = str(error).split('"')
            err = f'Bad argument, expected "{args[3]}" to be type "{args[1]}"'

        await ctx.channel.send(embed=embed(
            title='Error',
            description=(
                f'{err}\n\n'
                f'{info[0]}\n\n'
                f'{info[1]}\n\n'
                f'{info[2]}'
            )
        ))

    elif isinstance(error, commands.DisabledCommand):
        await ctx.channel.send(embed=embed(title='Error', description='This command is not available at this moment'))
    
    else:
        log.error(''.join(format_exception(None, error, error.__traceback__)))
        await ctx.channel.send(embed=embed(title='Error', description=f'{type(error).__name__}: {error}'))



@manager.command('invite')
@check(Permissions(admin_only=True))
@cooldowns.check(1)
async def cmd_invite(ctx: commands.Context, user: User):
    _embed = embed(title='Bot Invite', description='Click on the button below to get the bot invite!')
    await ctx.channel.send(embed=_embed, view=InviteButton())




def application_run():
    # task: Optional[asyncio.Task[None]] = None

    # async def client_loop():
    #     try:
    #         await client.connect()
    #     except:
    #         log.error(format_exc())
    #         if task and not task.done():
    #             task.cancel()

    async def loop():
        discord.utils.setup_logging(
            handler=root.log_handler,
            formatter=Formatter(),
            level=L_ERROR,
            root=False
        )
        # asyncio.create_task(client_loop())
        
        async with manager:
            try:
                await manager.start('MTM2NjA2MDYxMzE0Njc3MTQ4Nw.GyVHbD.xfOzJSlVykgvRYMyxr2SLq93Osk7CGbs6HyoqU')
            
            except asyncio.CancelledError:
                log.warning('Stop.')

            except:
                log.error(format_exc())
    asyncio.run(loop())