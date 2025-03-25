import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button, select, button
import os
from dotenv import load_dotenv

load_dotenv()

# Load token from .env
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot_config = {}  # In-memory config per guild


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")


class SettingsView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=300)
        self.guild = guild
        self.watched_user = None
        self.source_channel = None
        self.destination_channel = None

        # Prepare dropdown options
        members = [m for m in guild.members if not m.bot]
        user_options = [
            discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members
        ][:25]  # Discord limit

        channel_options = [
            discord.SelectOption(label=c.name, value=str(c.id)) for c in guild.text_channels
        ][:25]

        self.user_select.options = user_options
        self.source_select.options = channel_options
        self.dest_select.options = channel_options

    @select(placeholder="👤 Select user to watch", row=0)
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.watched_user = int(select.values[0])
        await interaction.response.defer()

    @select(placeholder="📥 Select source channel", row=1)
    async def source_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.source_channel = int(select.values[0])
        await interaction.response.defer()

    @select(placeholder="📤 Select destination channel", row=2)
    async def dest_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.destination_channel = int(select.values[0])
        await interaction.response.defer()

    @button(label="💾 Save Settings", style=discord.ButtonStyle.green, row=3)
    async def save_button(self, interaction: discord.Interaction, button: Button):
        if not all([self.watched_user, self.source_channel, self.destination_channel]):
            await interaction.response.send_message("⚠️ Please select all settings before saving.", ephemeral=True)
            return

        bot_config[self.guild.id] = {
            "watched_user": self.watched_user,
            "source_channel": self.source_channel,
            "destination_channel": self.destination_channel
        }

        await interaction.response.send_message("✅ Settings saved!", ephemeral=True)
        self.stop()


@bot.tree.command(name="settings", description="Configure the bot's repost settings")
@app_commands.checks.has_permissions(administrator=True)
async def settings(interaction: discord.Interaction):
    view = SettingsView(interaction.guild)
    await interaction.response.send_message("🛠 Configure the bot settings below:", view=view, ephemeral=True)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = message.guild.id
    config = bot_config.get(guild_id)

    if config:
        if (
            message.author.id == config.get("watched_user") and
            message.channel.id == config.get("source_channel")
        ):
            dest_channel = bot.get_channel(config.get("destination_channel"))
            if dest_channel:
                files = [await a.to_file() for a in message.attachments]
                content = f"**{message.author.display_name} said:** {message.content}"
                await dest_channel.send(content, files=files)

    await bot.process_commands(message)


bot.run(TOKEN)