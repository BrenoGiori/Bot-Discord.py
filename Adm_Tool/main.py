import discord
import os
import asyncio

from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

import firebase_admin
from firebase_admin import credentials, firestore

db = None

def initialize_firebase():
    global db                      # Seu caminho para o arquivo JSON
    cred = credentials.Certificate('C:/Users/user1/Arquivo/python/bot/JSON/serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase inicializado com sucesso.")


permissoes = discord.Intents.default()
permissoes.messages = True
permissoes.message_content = True
permissoes.members = True
bot = commands.Bot(command_prefix=".", intents = permissoes) 

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Funcionando")

     # Registra as views persistentes após carregar os cogs
    for cog in bot.cogs.values():
        if hasattr(cog, "setup_persistent_views"):
            await cog.setup_persistent_views()

async def load_cogs():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            await bot.load_extension(f"commands.{filename[:-3]}")  # Remove o '.py' para carregar o módulo

async def main():
    initialize_firebase()
    bot.db = db 

    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())
# Usando asyncio.run(main()), você pode realizar configurações adicionais (como conexões a bancos de dados ou APIs externas) antes de iniciar o bot.