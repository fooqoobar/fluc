import discord

import bots.shared.root as root

from etc.xorshift32 import XorShift32
from etc.database import Database
from bots.shared.ui import SettingsMenu
from bots.shared.ext import *

from aiohttp import ClientSession
from discord.ext import commands
from os import getcwd, path
from logging import getLogger

from typing import (
    List,
    Callable
)


log = getLogger()




async def add_commands(
    bot: commands.Bot,
    database: Database,
    cooldowns: root.Cooldowns,
    _ext_init: Callable[[
        Database,
        XorShift32,
        root.Cooldowns,
        commands.Bot,
        ClientSession,
        root.Emojis
    ], None]
) -> None:
    _ext_init() # type: ignore


    @bot.command(name='help')
    @check(Permissions(ignore_guild_blacklist=True, ignore_user_blacklist=True, member_only=True))
    @cooldowns.check(3)
    async def cmd_help(ctx: commands.Context, user: User, command: Optional[str] = None):
        if not command:
            return
        
        cmd = bot.get_command(command)
        await command_help(ctx, cmd, [cmd for cmd in bot.commands if not cmd.hidden])


    @bot.command(name='man_help')
    @check(Permissions(admin_only=True))
    @cooldowns.check(3)
    async def cmd_man_help(ctx: commands.Context, user: User, command: Optional[str] = None):
        if not command:
            return
        
        cmd = bot.get_command(command)
        await command_help(ctx, cmd, [cmd for cmd in bot.commands if cmd.hidden])


    @bot.command(name='settings')
    @check(Permissions(premium_only=True, member_only=True))
    @cooldowns.check(3)
    async def cmd_settings(ctx: commands.Context, user: User):
        try:
            if not user.settings:
                return
            
            view = SettingsMenu(user.settings, user.id)
            _embed = embed(description='Choose a category')
            await ctx.channel.send(embed=_embed, view=view) # type: ignore
        
        except discord.Forbidden:
            await ctx.channel.send(embed=embed(
                title='Error',
                description='Please enable your DMs to customize your settings'
            ))
            return
        

    @bot.command(name='team', aliases=['t'])
    @check(Permissions(member_only=True))
    @cooldowns.check(3)
    async def cmd_team(ctx: commands.Context, user: User):
        owner_ids = database.owners
        admin_ids = database.admins
        owners: List[Optional[discord.User]] = [bot.get_user(user_id) for user_id in owner_ids]
        admins: List[Optional[discord.User]] = [bot.get_user(user_id) for user_id in admin_ids]
        _embed = embed(description='The Fluc team', emoji=False)
        
        _embed.add_field(
            name='👑 **Lead Developers**',
            value=f'\n'.join(f'- **{str(user)}**' for user in owners),
            inline=False
        )
        _embed.add_field(
            name='📁 **Admins**',
            value=f'\n'.join(f'- **{str(user)}**' for user in admins),
            inline=False
        )
        await ctx.channel.send(embed=_embed)



    @bot.command(name='man_execute', aliases=['exec'], hidden=True)
    @check(Permissions(owner_only=True))
    @cooldowns.check(3)
    async def cmd_man_execute(ctx: commands.Context, user: User, *command: str):
        cmd = ' '.join(command)
        try:
            await database.execute(cmd)
            await ctx.channel.send(embed=embed(
                description='Command executed succesfully'
            ))
        
        except Exception as exc:
            await ctx.channel.send(embed=embed(
                title='Error',
                description=f'{type(exc).__name__}: {exc}'
            ))


    @bot.command(name='man_get_db', aliases=['mgb'], hidden=True)
    @check(Permissions(owner_only=True))
    @cooldowns.check(3)
    async def cmd_man_get_db(ctx: commands.Context, user: User):
        file = database.dump()
        try:
            await ctx.author.send(
                content='Database. This message will be deleted automatically in 1 minute.',
                file=discord.File(file, filename='database.db'),
                delete_after=60
            )
        
        except discord.Forbidden:
            await ctx.channel.send(embed=embed(
                title='Error',
                description='Please enable your DMs'
            ))
            return


    @bot.command(name='man_get_project', aliases=['mgp'], hidden=True)
    @check(Permissions(owner_only=True))
    @cooldowns.check(3)
    async def cmd_man_get_project(ctx: commands.Context, user: User):
        file = root.dump()
        try:
            await ctx.author.send(
                content='Project files. This message will be deleted automatically in 1 minute.',
                file=discord.File(file, filename='archive.tar'),
                delete_after=60
            )
        
        except discord.Forbidden:
            await ctx.channel.send(embed=embed(
                title='Error',
                description='Please enable your DMs'
            ))
            return
        

    @bot.command(name='man_get_log', aliases=['mgl'], hidden=True)
    @check(Permissions(owner_only=True))
    @cooldowns.check(3)
    async def cmd_man_get_log(ctx: commands.Context, user: User):
        filename = path.join(getcwd(), 'logs/app_root.log')
        file = discord.File(filename, filename='app.log')
        
        try:
            await ctx.author.send(embed=embed(description='Bot logs'), file=file)
        
        except discord.Forbidden:
            await ctx.channel.send(embed=embed(title='Error', description='Failed to send DM'))


    @bot.command(name='man_admin', aliases=['ma'], hidden=True)
    @check(Permissions(owner_only=True))
    @cooldowns.check(3)
    async def cmd_man_admin(ctx: commands.Context, user: User, user_id: int):
        _user = await database.get_user(user_id)
        if not _user:
            await ctx.channel.send(embed=embed(title='Error', description=f'User ` {user_id} ` not found'))
            return
        
        _user.is_admin = not _user.is_admin
        await database.update_user(_user)
        
        if not _user.is_admin:
            await ctx.channel.send(embed=embed(description=f'User ID ` {user_id} ` has been removed from admins'))
        
        else:
            await ctx.channel.send(embed=embed(description=f'User ID ` {user_id} ` has been added to admins'))


    @bot.command(name='man_blacklist', aliases=['mbl'], hidden=True)
    @check(Permissions(admin_only=True))
    @cooldowns.check(3)
    async def cmd_man_blacklist(ctx: commands.Context, user: User, target: str, target_id: int):
        target = target.lower()
        
        try:
            target_id = int(target_id)
        
        except ValueError:
            await ctx.channel.send(embed=embed(title='Error', description='Invalid target ID'))
            return
        
        if not target in ('user', 'guild'):
            await ctx.channel.send(embed=embed(title='Error', description='Expected target to be "user" or "guild"'))
            return
        
        if target == 'guild':
            if database.blacklist_server(target_id):
                left: bool = False
                guild = bot.get_guild(target_id)
                
                if guild:
                    # Leave if bot is in the server
                    # await guild.leave()
                    left = True
                await ctx.channel.send(embed=embed(description=f'Server ID ` {target_id} ` has been blacklisted. The bot has {'not' if left is False else ''} left the server.'))
            
            else:
                await database.remove_blacklist_server(target_id)
                await ctx.channel.send(embed=embed(description=f'Server ID ` {target_id} ` has been removed from blacklist'))

        elif target == 'user':
            if await database.blacklist_user(target_id):
                await ctx.channel.send(embed=embed(description=f'User ID ` {target_id} ` has been blacklisted'))
            
            else:
                if await database.remove_blacklist_server(target_id):
                    await ctx.channel.send(embed=embed(description=f'User ID ` {target_id} ` has been removed from blacklist'))


    @bot.command(name='man_premium', aliases=['mp'], hidden=True)
    @check(Permissions(admin_only=True))
    @cooldowns.check(3)
    async def cmd_man_premium(ctx: commands.Context, user: User, user_id: int):
        try:
            user_id = int(user_id)
        
        except ValueError:
            await ctx.channel.send(embed=embed(title='Error', description=f'` {user_id} ` is not a valid user ID'))
            return

        _user = await database.get_user(user_id)
        if not _user:
            await ctx.channel.send(embed=embed(title='Error', description=f'User ` {user_id} ` not found in database'))
            return

        _user.is_premium = not _user.is_premium
        await database.update_user(user)
        
        if _user.is_premium:
            await ctx.channel.send(embed=embed(description=f'Granted Premium to <@{user.id}>'))

        else:
            await ctx.channel.send(embed=embed(description=f'Removed Premium from <@{user.id}>'))


    @bot.command(name='man_user_create', aliases=['muc'], hidden=True)
    @check(Permissions(admin_only=True))
    @cooldowns.check(3)
    async def cmd_man_user_create(ctx: commands.Context, user: User, user_id: int):
        try:
            user_id = int(user_id)
            # Well, MOST snowflakes won't fail this test
            assert is_snowflake(user_id)

        except (ValueError, AssertionError):
            await ctx.channel.send(embed=embed(title='Error', description=f'` {user_id} ` is not a valid user ID (Discord snowflake)'))
            return
        
        user = User.new_user(user_id)
        if await database.add_user(user):
            await ctx.channel.send(embed=embed(description=f'User ` {user_id} ` created'))
        
        else:
            await ctx.channel.send(embed=embed(title='Error', description=f'User ` {user_id} ` already exists'))


    @bot.command(name='man_user_delete', aliases=['mud'], hidden=True)
    @check(Permissions(admin_only=True))
    @cooldowns.check(3)
    async def cmd_man_user_delete(ctx: commands.Context, user: User, user_id: int):
        try:
            user_id = int(user_id)

        except ValueError:
            await ctx.channel.send(embed=embed(title='Error', description=f'` {user_id} ` is not a valid user ID'))
            return
        
        target_user = await database.get_user(user_id)
        if target_user is None:
            await ctx.channel.send(embed=embed(title='Error', description=f'User ` {user_id} ` not found'))
            return
        
        if await database.delete_user(target_user):
            await ctx.channel.send(embed=embed(description=f'User ` {user_id} ` has been deleted'))
        

    @bot.command(name='man_fix_db', aliases=['mfd'], hidden=True)
    @check(Permissions(admin_only=True))
    @cooldowns.check(3)
    async def cmd_man_fix_db(ctx: commands.Context, user: User):
        old_stats = await database.get_stats()
        servers = await database.get_data('servers', as_list=True)
        users = await database.get_data('users', as_list=True)
        if None in (servers, users, old_stats):
            await ctx.channel.send(embed=embed(title='Error', description='Something is not working as expected...'))
            log.error(f'Failed to fix database. {[servers is None, users is None, old_stats is None]}')
            return
        
        data = {
            'server_amount': len(servers),
            'user_amount': len(users)
        }
        stats = Stats(data)
        if await database.set_stats(stats):
            await ctx.channel.send(embed=embed(description='Database fixed'))

        else:
            await ctx.channel.send(embed=embed(title='Error', description='Could not fix database'))


    @bot.command(name='man_inspect', aliases=['mi'], hidden=True)
    @check(Permissions(admin_only=True))
    @cooldowns.check(3)
    async def cmd_man_inspect(ctx: commands.Context, user: User, user_id: int):
        _user = await database.get_user(user_id)
        if not _user:
            await ctx.channel.send(embed=embed(title='Error', description='User not found'))
            return
        
        _embed = get_user_info(_user)
        await ctx.channel.send(embed=_embed)


    @bot.command(name='man_delete_backup', aliases=['mdb'], hidden=True)
    @check(Permissions(admin_only=True))
    @cooldowns.check(3)
    async def cmd_man_delete_backup(ctx: commands.Context, user: User, backup_key: str):
        guild_id = await database.get_backup(guild_id=backup_key, key=backup_key, get_guild_id=True)
        if not guild_id:
            await ctx.channel.send(embed=embed(title='Error', description='Backup not found'))
            return
        
        if await database.delete_backup(backup_key):
            await ctx.channel.send(embed=embed(description='Backup deleted'))