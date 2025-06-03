import discord
import requests
import emoji

from logging import getLogger
from datetime import datetime, UTC
from discord import app_commands
from discord.ext import commands
from concurrent.futures import ThreadPoolExecutor
from traceback import format_exc

from etc.logger import create_logger
from etc.xorshift32 import XorShift32


create_logger(''.join(__name__.split('.')[-1:]))
log = getLogger()



TOKEN = 'MTM2MjQzNjYzODUwNDEyODcwMg.G4dt_D.HeQjdgnG9TahzDghPfreKmIl_kzhobi4uRoW_M'
# TOKEN = 'MTM0ODM2MTAyMTUyOTUyMjE5Ng.GZ5yoR.whB6rN5WbPQzZWkAuVdhHcbhjQPGDRyUd705bU'

xorshift32 = XorShift32()
all_emojis = list(emoji.EMOJI_DATA.keys())
user_cooldowns = {}
bot = commands.Bot(
    command_prefix='',
    intents=discord.Intents.all(),
    help_command=None
)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        log.info(f'synced {len(synced)} commands.')

    except Exception as e:
        log.info(f'Failed to sync commands: {e}')
    log.info(f'{bot.user} is online!')
    

@bot.event
async def on_command_error(interaction: discord.Interaction, error: Exception):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f'You\'re on cooldown for {error.retry_after} more second{'s' if error.retry_after > 1 else ''}.', 
            ephemeral=True
        )



@bot.tree.command(name='send', description='Set up the fun commands!')
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def spam(interaction: discord.Interaction):
    global user_cooldowns

    def send():
        emoji_data = ''.join(xorshift32.choice(all_emojis, amount=500))
        with requests.post(f'https://discord.com/api/v10/webhooks/{app_id}/{token}', json={'content': content.format(random_quote(), xorshift32.randstr(5), emoji_data)}) as response:
            log.info(f'User: {interaction.user.name}\nStatus: {response.status_code} // {response.json().get('message', 'No message')}')
    
    
    def random_quote():
        quotes = [
            'Rekted',
            'Owned',
            'Raided',
            'Destroyed',
            'Shamed',
            'Spammed'
        ]
        return xorshift32.choice(quotes)
    
    
    now = datetime.now(UTC).timestamp()
    user_id = interaction.user.id

    if user_id in user_cooldowns and now - user_cooldowns[user_id] < 5:
        await interaction.response.send_message('Whoa there! You can only use this command 1 time every 5 seconds', ephemeral=True)
        return

    user_cooldowns[user_id] = now

    token = interaction.token
    app_id = interaction.application_id
    content = '> # {} By Fluc | discord.com/invite/nxn // {} {}'
    await interaction.response.send_message("```fix\n> Sending messages...\n```", ephemeral=True)

    # Workers ❌
    # Slaves ✅
    with ThreadPoolExecutor(max_workers=50) as executor:
        for _ in range(5):
            executor.submit(send)



def application_run():
    try:
        bot.run(TOKEN)
        
    except Exception:
        log.error(format_exc())