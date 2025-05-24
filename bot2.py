import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
from collections import defaultdict, Counter
import os
import json

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True
intents.reactions = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    allowed_mentions=discord.AllowedMentions.none()
)

LANGUAGES = {
    '🇬🇧': 'en',
    '🇪🇸': 'es',
    '🇵🇹': 'pt',
    '🇫🇷': 'fr',
    '🇩🇪': 'de',
    '🇮🇹': 'it',
    '🇨🇳': 'zh-CN'
}

LANGUAGE_FILE = "languages.json"

def load_languages():
    try:
        with open(LANGUAGE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_languages():
    with open(LANGUAGE_FILE, "w") as f:
        json.dump(user_languages, f)

user_languages = load_languages()

translation_stats = {
    "total": 0,
    "per_user": defaultdict(int),
    "per_language": Counter()
}

# Dropdown de idioma
class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=lang, value=code) for lang, code in [
            ("English", "en"), ("Português", "pt"), ("Español", "es"),
            ("Français", "fr"), ("Deutsch", "de"), ("Italiano", "it"), ("中文", "zh-CN")
        ]]
        super().__init__(
            custom_id="language_select",
            placeholder="Choose your language...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_languages[str(interaction.user.id)] = self.values[0]
        save_languages()
        await interaction.response.send_message(
            f"🌍 Language set to `{self.values[0]}`!", ephemeral=True
        )

class LanguageMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LanguageSelect())

# Eventos
@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    bot.add_view(LanguageMenu())

    channel = discord.utils.get(bot.get_all_channels(), name="choose-language")
    if channel:
        pinned = await channel.pins()
        for msg in pinned:
            if msg.author == bot.user and msg.content.startswith("🌐"):
                break
        else:
            sent = await channel.send("🌐 **Select your preferred language below:**", view=LanguageMenu())
            await sent.pin()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    try:
        if not message.webhook_id:
            await message.add_reaction("🌍")
    except Exception as e:
        print(f"[Reaction error] {e}")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if str(reaction.emoji) != "🌍":
        return

    message = reaction.message
    user_id = str(user.id)

    if user_id not in user_languages:
        # Avisar no canal #choose-language
        channel = discord.utils.get(bot.get_all_channels(), name="choose-language")
        if channel:
            try:
                await channel.send(f"{user.mention} ❗ Please select your language using the menu above.", delete_after=10)
            except:
                pass
        return

    if user.id == message.author.id:
        return  # Silenciosamente ignora, sem notificar

    lang = user_languages[user_id]

    try:
        translated = GoogleTranslator(source='auto', target=lang).translate(message.content)
    except Exception as e:
        print(f"[Translation error] {e}")
        return

    embed = discord.Embed(description=translated, color=discord.Color.blue())
    embed.set_author(
        name=f"{message.author.display_name} ({lang})",
        icon_url=message.author.display_avatar.url
    )

    try:
        sent_msg = await message.channel.send(content=user.mention, embed=embed, silent=True)
        await sent_msg.delete(delay=15)
    except Exception as e:
        print(f"[Send/delete error] {e}")

    translation_stats["total"] += 1
    translation_stats["per_user"][user.id] += 1
    translation_stats["per_language"][lang] += 1

# Comandos
@bot.hybrid_command(name="stats", description="Show translation statistics")
async def stats(ctx):
    total = translation_stats["total"]
    users = len(translation_stats["per_user"])
    top_langs = translation_stats["per_language"].most_common(5)

    embed = discord.Embed(title="📊 Translation Stats", color=discord.Color.green())
    embed.add_field(name="Total translations", value=str(total), inline=False)
    embed.add_field(name="Users translated", value=str(users), inline=False)
    embed.add_field(name="Top languages", value="\n".join([f"{l} - {c}" for l, c in top_langs]) or "None yet.")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="language", description="(Legacy) Use the dropdown in #choose-language")
async def language_cmd(ctx):
    await ctx.send("🌐 Use the menu in #choose-language to set your language.", ephemeral=True)

# Executa
def run_bot():
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("❌ Token not found. Please set DISCORD_BOT_TOKEN.")
    else:
        bot.run(TOKEN)
