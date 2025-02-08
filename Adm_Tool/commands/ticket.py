import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, Select

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.ticket_counters = {}

    async def setup_persistent_views(self):
        # Registra a view persistentemente
        ticket_view = TicketView(self)
        self.bot.add_view(ticket_view)

        ticket_view_close = CloseTicketView(self)
        self.bot.add_view(ticket_view_close)

        await self.load_ticket_counters()

    async def load_ticket_counters(self):
        settings_ref = self.db.collection('settings') #Nome da coleção no Firestore, fica a sua escolha
        docs = settings_ref.limit(100).stream()
        for doc in docs:
            guild_id = int(doc.id)
            self.ticket_counters[guild_id] = doc.to_dict().get('ticket_counter', 0)
            # print(f"Carregado contador de tickets para {guild_id}: {self.ticket_counters[guild_id]}")

    def get_ticket_counter(self, guild_id):
        # print(f"Obtendo contador de tickets para {guild_id}: {self.ticket_counters.get(guild_id, 0)}")
        return self.ticket_counters.get(guild_id, 0)
    
    def update_ticket_counter(self, guild_id, counter):
        self.ticket_counters[guild_id] = counter
        doc_ref = self.db.collection('settings').document(str(guild_id))
        doc_ref.update({'ticket_counter': counter})
        # print(f"Contador de tickets atualizado para {guild_id}: {counter}")


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
            print(f"{guild_id} Erro ao buscar Steam ID: {e}")
            return None
        

    @discord.app_commands.command(name='ticket', description="Cria o embed responsável pelos tickets.")
    async def ticket(self, interaction: discord.Interaction, canal: discord.TextChannel):
        guild_id = interaction.guild.id
        ticket_counter = self.get_ticket_counter(guild_id)

        if interaction.user.guild_permissions.ban_members:
            modal = ConfigTicketModal(canal=canal, ticket_cog=self, guild_id=guild_id, ticket_counter=ticket_counter)
            await interaction.response.send_modal(modal)
            return

        await interaction.response.send_message(
            'Você não tem permissão para utilizar esse comando.', ephemeral=True
        )


class ConfigTicketModal(Modal):
    def __init__(self, canal, ticket_cog, guild_id, ticket_counter):
        super().__init__(title="Configuração do ticket")
        self.canal = canal
        self.ticket_cog = ticket_cog
        self.guild_id = guild_id
        self.ticket_counter = ticket_counter

        self.titulo = TextInput(label="Título", placeholder="Título para o embed do sistema de tickets.")
        self.add_item(self.titulo)

        self.description = TextInput(
            label="Descrição", 
            placeholder="Descrição para o embed do sistema de tickets.",
            style=discord.TextStyle.paragraph,
            )
        self.add_item(self.description)

        self.imagem_url = TextInput(
            label="Imagem", 
            placeholder="campo para Url da imagem do Embed", 
            required=False)
        self.add_item(self.imagem_url)

    async def on_submit(self, interaction: discord.Interaction):
        description_with_newlines = self.description.value.replace("\\n", "\n")

        embed = discord.Embed(
            title=self.titulo.value,
            description=description_with_newlines,
            color=discord.Color.blue(),
        )
        embed.set_image(url=self.imagem_url.value)
        embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url)

        visualizacao = TicketView(ticket_cog=self.ticket_cog)

        embed2 = discord.Embed(
            title = "Embed",
            description = f"Enviado com sucesso para {self.canal.mention}.",
            color=discord.Color.blue()
        )
        
        await self.canal.send(embed=embed, view=visualizacao)
        await interaction.response.send_message(embed=embed2, ephemeral=True)


class TicketModal(Modal):
    def __init__(self, ticket_cog, guild_id, user_id):
        super().__init__(title="Abrir Ticket")
        self.ticket_cog = ticket_cog
        self.guild_id = guild_id
        self.user_id = user_id

        self.resumo = TextInput(label="Resumo", placeholder="Descreva brevemente o motivo do ticket.")
        self.add_item(self.resumo)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Aguarda antes de enviar resposta

    # Atualizar o contador no banco
        ticket_counter = self.ticket_cog.get_ticket_counter(self.guild_id) + 1
        self.ticket_cog.update_ticket_counter(self.guild_id, ticket_counter)

        ticket_name = f"Ticket #{ticket_counter} - {interaction.user}"

        #Banco de Dados - Steam ID
        steam_id = await self.ticket_cog.get_steam_id_from_db(self.user_id, self.guild_id)
    
        if steam_id:
            SteamIDEmbed = f'`{steam_id}`'
        else:
            SteamIDEmbed = f'`Não possui Steam ID vinculado a sua conta`.'

        #Embeds - Ticket e Thread
        if isinstance(interaction.channel, discord.TextChannel):
            thread = await interaction.channel.create_thread(
                name=ticket_name,
                type=discord.ChannelType.private_thread,
            )

            await thread.add_user(interaction.user)

            embed_Thread = discord.Embed(
                title=f"{interaction.user} abriu este ticket.",
                description=f"**Steam ID:**\n{SteamIDEmbed} \n\n**Motivo do Ticket:**\n{self.resumo.value}",
                color=discord.Color.blue(),
                timestamp = discord.utils.utcnow()
            )

            embed_Ticket_New = discord.Embed(
                title="Ticket",
                description=f"Criado com sucesso: {thread.mention}",
                color=discord.Color.blue()
            )

            view = CloseTicketView(ticket_cog=self.ticket_cog)

            await thread.send(embed=embed_Thread, view=view)

            await interaction.followup.send(embed=embed_Ticket_New, ephemeral=True)

        else:
            await interaction.followup.send(
            "Este canal não suporta a criação de tópicos privados.", ephemeral=True
        )


class TicketView(View):
    def __init__(self, ticket_cog):
        super().__init__(timeout=None)
        self.ticket_cog = ticket_cog

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="persistent:open_ticket")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        modal = TicketModal(ticket_cog=self.ticket_cog, guild_id=guild_id, user_id=user_id)
        await interaction.response.send_modal(modal)


class CloseTicketView(View):
    def __init__(self, ticket_cog):
        super().__init__(timeout=None)
        self.ticket_cog = ticket_cog

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def fechar_ticket(self, interaction: discord.Interaction, button: Button):
        if interaction.user.guild_permissions.manage_threads:
            await interaction.response.send_message("O ticket foi fechado com sucesso.", ephemeral=True)
            await interaction.channel.edit(archived=True, locked=True)
        else:
            await interaction.response.send_message(
                "Você não tem permissão para fechar tickets.", ephemeral=True
            )
    
    @discord.ui.button(label="Fechar com motivo", style=discord.ButtonStyle.danger,custom_id="reason_close_ticcket")
    async def fechar_com_motivo(self, interaction: discord.Interaction, button: Button):
        if interaction.user.guild_permissions.manage_threads:
            modal = TicketCloseReason()
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message(
                "Você não tem permissão para fechar tickets.", ephemeral=True
            )


class TicketCloseReason(Modal):
    def __init__(self):
        super().__init__(title="Close Ticket")

        self.motivo = TextInput(
            label="Motivo",
            placeholder="Descreva o motivo para fechar este ticket.",
            required=True,
            style=discord.TextStyle.paragraph,  # Estilo de texto para mensagens longas
        )
        self.add_item(self.motivo)

    async def on_submit(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.Thread) and not interaction.channel.archived:
            
            embed = discord.Embed(
                title=f"Ticket fechado",
                description=f"Motivo: {self.motivo.value}\n\n Ticket fechado por {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp = discord.utils.utcnow()
            )
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message(
                "O ticket foi fechado e arquivado com sucesso.", ephemeral=True
            )
            await interaction.channel.edit(archived=True, locked=True)
        else:
            await interaction.response.send_message(
                "Erro: Não é possível fechar este ticket. Ele pode já estar arquivado.", ephemeral=True
            )

async def setup(bot):
    cog = TicketCog(bot)
    await bot.add_cog(cog)
    await cog.setup_persistent_views()