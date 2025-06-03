#pyright: reportAttributeAccessIssue=false

from bots.shared.hints import *
from etc.database import (
    Settings,
    Database
)

from discord import (
    ui,
    Embed,
    ButtonStyle,
    Interaction
)

from typing import (
    List,
    Type,
    Mapping,
    Any
)




class Modal(ui.Modal):
    def __init__(self, title: str, settings: Settings, database: Database):
        self.settings: Settings = settings
        self.database: Database = database
        super().__init__(title=title, timeout=None)


    def parse(self, *args: Union[ui.TextInput, Any]) -> List[List[Any]]:
        result = []
        for arg in args:
            if arg is None or not getattr(arg, 'value', None):
                # Empty
                arg = []

            else:
                arg = str(arg.value)
            
            if len(arg) == 2:
                if '0' in arg or '1' in arg:
                    if arg == '00':
                        arg = [False]
                    
                    elif arg == '11':
                        arg = [True]

                    elif arg in ('10', '01'):
                        arg = [True, False]

            if isinstance(arg, str):
                arg = [item.strip() for item in arg.split('%')]
            result.append(arg)
        return result
    

    def set_results(self, category: str, results: Mapping[str, Any]) -> None:
        results = dict(results)
        for key, value in results.items():
            if value is None:
                # Do not overwrite unchanged settings
                results.pop(key)
 
        if category == 'reasons':
            self.settings.raw_data[category] = results['reasons']
            return
        self.settings.raw_data[category].update(results)


    async def update(self, interaction: Interaction):
        user = await self.database.get_user(interaction.user.id)
        if not user:
            return
        
        user.settings.raw_data = self.settings.raw_data
        if self.database.update_user(user):
            await interaction.response.send_message(embed=Embed(
                description='Settings updated'
            ), ephemeral=True)

        else:
            await interaction.response.send_message(embed=Embed(
                description='Settings not updated'
            ), ephemeral=True)
    
    
    async def on_submit(self, interaction: Interaction):
        await self.submit() # type: ignore
        await self.update(interaction)



class ReasonModal(Modal):
    reasons = ui.TextInput(label='Reasons', required=False)

    async def submit(self):
        self.set_results('reasons', {'reasons': self.parse(self.reasons)[0]})



class ChannelModal(Modal):
    name = ui.TextInput(label='Names', required=False)
    topic = ui.TextInput(label='Topic', required=False)
    nsfw = ui.TextInput(label='NSFW [0/1]', required=False, min_length=1, max_length=2)
    slowmode_delay = ui.TextInput(label='Slowmode Delay', required=False)

    async def submit(self):
        results = self.parse(self.name, self.topic, self.nsfw, self.slowmode_delay)
        data: ChannelDict = {
            'name': results[0],
            'topic': results[1],
            'nsfw': results[2],
            'slowmode_delay': results[3]
        }
        self.set_results('channel', data)



class WebhookModal(Modal):
    name = ui.TextInput(label='Names', required=False)

    async def submit(self):
        self.set_results('webhook', {'name': self.parse(self.name)[0]})



class RoleModal(Modal):
    name = ui.TextInput(label='Name', required=False)
    # I swear they'll mess it up and then complain.
    # Not everyone understands stuff like this
    permissions = ui.TextInput(label='Permissions', required=False)
    color = ui.TextInput(label='Colors', required=False)
    hoist = ui.TextInput(label='Hoist [0/1]', required=False, min_length=1, max_length=2)
    mentinable = ui.TextInput(label='Mentinable [0/1]', required=False, min_length=1, max_length=2)

    async def submit(self):
        results = self.parse(self.name, self.permissions, self.color, self.hoist, self.mentinable)
        for i, color in enumerate(results[3]):
            # HEX -> DEC (discord.Color support (it doesn't really matter but I like this way ok?))
            color = color.removeprefix('#')
            # HEX (base 16) to an integer
            color = int(color, 16)
            results[3][i] = color

        data: RoleDict = {
            'name': results[0],
            'permissions': results[1],
            'color': results[2],
            'hoist': results[3],
            'mentionable': results[4]
        }
        self.set_results('role', data)



class EmojiModal(Modal):
    name = ui.TextInput(label='Names', required=False)
    image = ui.TextInput(label='Images [url]', required=False)

    async def submit(self):
        results = self.parse(self.name, self.image)
        data: EmojiDict = {
            'name': results[0],
            'image': results[1]
        }
        self.set_results('role', data)



class StickerModal(Modal):
    name = ui.TextInput(label='Names', required=False)
    image = ui.TextInput(label='Images [url]', required=False)
    description = ui.TextInput(label='Descriptions', required=False)
    emoji = ui.TextInput(label='Emojis', required=False)

    async def submit(self):
        results = self.parse(self.name, self.image, self.description, self.emoji)
        data: StickerDict = {
            'name': results[0],
            'image': results[1],
            'description': results[2],
            'emoji': results[3]
        }
        self.set_results('sticker', data)



class MemberModal(Modal):
    nick = ui.TextInput(label='Nicknames', required=False)
    mute = ui.TextInput(label='Mute [0/1]', required=False, min_length=1, max_length=2)
    deafen = ui.TextInput(label='Deafen [0/1]', required=False, min_length=1, max_length=2)
    supress = ui.TextInput(label='Supress [0/1]', required=False, min_length=1, max_length=2)
    timed_out_until = ui.TextInput(label='Timeout Durations', required=False)

    async def submit(self):
        results = self.parse(self.nick, self.mute, self.deafen, self.supress, self.timed_out_until)
        data: MemberDict = {
            'nick': results[0],
            'mute': results[1],
            'deafen': results[2],
            'supress': results[3],
            'timed_out_until': results[4]
        }
        self.set_results('member', data)



class GuildModal(Modal):
    name = ui.TextInput(label='Names', required=False)
    icon = ui.TextInput(label='Icons [url]', required=False)

    async def submit(self):
        results = self.parse(self.name, self.icon)
        data: GuildDict = {
            'name': results[0],
            'icon': results[1]
        }
        self.set_results('guild', data)



class MessageModal(Modal):
    content = ui.TextInput(label='Content', required=False)
    tts = ui.TextInput(label='Text-To-Speech [0/1]', required=False, min_length=1, max_length=2)
    username = ui.TextInput(label='Usernames', required=False)
    avatar_url = ui.TextInput(label='Avatars [url]', required=False)
    # Embeds supported SOON

    async def submit(self):
        results = self.parse(self.content, self.tts, self.username, self.avatar_url)
        data: MessageDict = {
            'content': results[0],
            'tts': results[1],
            'username': results[2],
            'avatar_url': results[3],
            'embed': [None]
        }
        self.set_results('message', data)



class PrefixModal(Modal):
    prefixes = ui.TextInput(label='Prefix')

    async def submit(self):
        results = self.parse(self.prefixes)
        data: PrefixDict = {
            'prefixes': results[0]
        }
        self.set_results('prefix', data)



class Button(ui.View):
    def __init__(self, modal: Optional[Type[Modal]], settings: Settings, database: Database):
        super().__init__(timeout=None)
        self.settings: Settings = settings
        self.database: Database = database
        self.modal: Optional[Type[Modal]] = modal
        # There's nothing to explain here

        if self.modal:
            if isinstance(self.modal, type):
                self.name: str = self.modal.__name__.removesuffix('Modal') + ' Customization'
            
            else:
                self.name: str = self.modal.__class__.__name__.removesuffix('Modal') + ' Customization'


    @ui.button(label='☕ Customize', style=ButtonStyle.blurple)
    async def customize(self, interaction: Interaction, button: ui.Button):
        if self.modal is None:
            self.settings.raw_data = self.database.default_settings
            await Modal('', self.settings, self.database).update(interaction)

        else:
            await interaction.response.send_modal(self.modal(self.name, self.settings, self.database))
