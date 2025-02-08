import discord
from discord.ext import commands

import requests
import os

import re

from dotenv import load_dotenv
load_dotenv()
STEAM_API_KEY = os.getenv('STEAM_API_KEY')

class registrar_steamID(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def cadastro_steamID64(self, member, user_id, steam_id_64, guild_id):
        doc_ref = self.db.collection('settings').document(str(guild_id)).collection('users').document(str(user_id))
        doc_ref.set({
            'member_name': str(member),
            'steam_id': steam_id_64
        }, merge=True)

    def verificar_steam_id(self, steam_id_64):
        # Verifica se o Steam ID existe na API da Steam 
        url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
        params = {
            "key": STEAM_API_KEY,
            "steamids": steam_id_64
        }
        
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            players = data.get("response", {}).get("players", [])
            return bool(players)  # Retorna True se o Steam ID for válido
        else:
            print("Erro ao acessar a API da Steam:", response.status_code)
            return None  # Retorna None em caso de erro
        
    # Regex para extrair o Steam ID64 de uma URL
    def extrair_steam_id(self, url: str) -> str:
        padrao = r"(\d{17})"  # Captura exatamente 17 dígitos
        match = re.search(padrao, url)
        return match.group(1) if match else None

    @discord.app_commands.command(name='registro', description='Csdastre o seu Steam ID64')
    async def registro(self, interaction: discord.Interaction, steam_id: str):
        user_id = interaction.user.id
        guild_id = interaction.guild.id
        member = interaction.user

        steam_id_64 = self.extrair_steam_id(steam_id)  # Extrai o Steam ID64 da URL, se houver

        # Verifica se o Steam ID existe antes de salvar
        existe = self.verificar_steam_id(steam_id_64)
        if existe is None:
            await interaction.response.send_message("❌ Erro ao acessar a API da Steam. Tente novamente mais tarde.", ephemeral=True)
        elif not existe:
            await interaction.response.send_message("⚠️ O Steam ID informado não existe. Verifique e tente novamente.", ephemeral=True)
        else:
            await self.cadastro_steamID64(member, user_id, steam_id_64, guild_id)
            await interaction.response.send_message("✅ Sua conta foi verificada com sucesso!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(registrar_steamID(bot))