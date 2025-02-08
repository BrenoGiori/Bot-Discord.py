import discord
from discord import app_commands
from discord.ext import commands

from google.cloud import firestore

class find_id(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def get_steam_id_from_db(self, user_id, guild_id):
        # Busca o Steam ID do usuário no Firebase.
        try:
            doc_ref = self.db.collection('settings').document(str(guild_id)).collection('users').document(str(user_id))
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict().get('steam_id')  # Retorna o Steam ID salvo
            else:
                return None  # Usuário não encontrado no Firestore
        except Exception as e:
            print(f"Erro ao buscar Steam ID: {e}")
            return None

    #Busca pelo discord id usando o Steam ID
    async def get_discord_ids_from_steam(self, steam_id, guild_id):
        # Busca todos os Discord IDs de usuários com o mesmo Steam ID.
        try:
            # Referência à coleção "users" dentro do documento do servidor
            users_ref = self.db.collection("settings").document(str(guild_id)).collection("users")

            # Certifique-se de que o Steam ID é string
            steam_id = str(steam_id)

            # Busca todos os usuários que têm esse Steam ID
            query = users_ref.where(filter=firestore.FieldFilter("steam_id", "==", steam_id)).stream()

            discord_ids = [doc.id for doc in query]  # Pegamos os IDs dos documentos (que são os Discord IDs)

            return discord_ids if discord_ids else None  # Retorna a lista de IDs ou None se não houver resultados
        except Exception as e:
            print(f"Erro ao buscar usuários pelo Steam ID: {e}")
            return None

    @discord.app_commands.command(name='get_steam', description='Recupera seu Steam ID salvo.')
    async def get_steam(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id

        steam_id = await self.get_steam_id_from_db(user_id, guild_id)
    
        if steam_id:
            await interaction.response.send_message(f"🔍 Seu Steam ID é: `{steam_id}`", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Você ainda não registrou um Steam ID!", ephemeral=True)


    @discord.app_commands.command(name='consult_steamid', description='Consulta o Steam ID salvo pelo Discord ID.')
    async def consult_steamid(self, interaction: discord.Interaction, user_id:str):
        guild_id = interaction.guild.id
        steam_id = await self.get_steam_id_from_db(user_id, guild_id)
        if steam_id:
            await interaction.response.send_message(f"🔍 O Steam ID do {user_id} é: `{steam_id}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ O {user_id} não vinculou um SteamID a sua conta", ephemeral=True)
        
    @discord.app_commands.command(name="find_steam", description="Encontre usuários pelo Steam ID.")
    async def find_steam(self, interaction: discord.Interaction, steam_id: str):
        guild_id = interaction.guild.id

        discord_ids = await self.get_discord_ids_from_steam(steam_id, guild_id)

        if discord_ids:
            user_list = []
            for discord_id in discord_ids:
                member = interaction.guild.get_member(int(discord_id))
                username = member.name if member else f"ID: {discord_id} (Não está no servidor)"
                user_list.append(f"🔹 {username}")

            user_list_str = "\n".join(user_list)
            await interaction.response.send_message(f"🔍 Steam ID `{steam_id}` pertence a:\n{user_list_str}", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Nenhum usuário encontrado com esse Steam ID.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(find_id(bot))