import discord
from discord.ext import commands, tasks
from deep_translator import GoogleTranslator
from collections import defaultdict, Counter
import os
import json
import asyncio

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

# Includes Polish (🇵🇱), Turkish (🇹🇷), and Welsh (🏴) languages
LANGUAGES = {
    '🇬🇧': 'en',
    '🇪🇸': 'es',
    '🇵🇹': 'pt',
    '🇫🇷': 'fr',
    '🇩🇪': 'de',
    '🇮🇹': 'it',
    '🇨🇳': 'zh-CN',
    '🇵🇱': 'pl',
    '🇹🇷': 'tr',
    '🏴': 'cy'
}

LANGUAGE_FILE = "user_languages.json"

def load_languages():
    try:
        with open(LANGUAGE_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ Loaded {len(data)} user language configurations")
            return data
    except FileNotFoundError:
        print(f"⚠️ File {LANGUAGE_FILE} not found, starting with empty configuration")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing {LANGUAGE_FILE}: {e}")
        print("🔄 Creating backup and starting fresh")
        # Create backup of corrupted file
        try:
            os.rename(LANGUAGE_FILE, f"{LANGUAGE_FILE}.backup")
        except:
            pass
        return {}
    except Exception as e:
        print(f"❌ Unexpected error loading languages: {e}")
        return {}

def save_languages():
    try:
        # Make backup before overwriting
        if os.path.exists(LANGUAGE_FILE):
            try:
                os.rename(LANGUAGE_FILE, f"{LANGUAGE_FILE}.temp")
            except:
                pass
        
        with open(LANGUAGE_FILE, "w", encoding='utf-8') as f:
            json.dump(user_languages, f, indent=2, ensure_ascii=False)
        
        # Verify that it was saved correctly
        with open(LANGUAGE_FILE, "r", encoding='utf-8') as f:
            saved_data = json.load(f)
            if len(saved_data) != len(user_languages):
                raise ValueError("Data verification failed after save")
        
        # Remove temporary backup if everything went well
        temp_file = f"{LANGUAGE_FILE}.temp"
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        print(f"✅ Saved {len(user_languages)} user configurations")
        
    except Exception as e:
        print(f"❌ Error saving languages: {e}")
        # Try to restore backup if it exists
        temp_file = f"{LANGUAGE_FILE}.temp"
        if os.path.exists(temp_file):
            try:
                os.rename(temp_file, LANGUAGE_FILE)
                print("🔄 Restored from backup")
            except:
                print("❌ Failed to restore backup")
        raise e

user_languages = load_languages()

translation_stats = {
    "total": 0,
    "per_user": defaultdict(int),
    "per_language": Counter()
}

# Store pairs (message.id, user.id) to avoid duplicate translations
translated_messages = set()

# Language dropdown
class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=lang, value=code) for lang, code in [
            ("English", "en"), ("Português", "pt"), ("Español", "es"),
            ("Français", "fr"), ("Deutsch", "de"), ("Italiano", "it"),
            ("中文", "zh-CN"), ("Polski", "pl"),
            ("Türkçe", "tr"), ("Cymraeg", "cy")
        ]]
        super().__init__(
            custom_id="language_select",
            placeholder="Choose your language...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        selected_lang = self.values[0]
        
        try:
            # Update in memory
            user_languages[user_id] = selected_lang
            
            # Save to file with validation
            save_languages()
            
            # Verify that it was saved correctly
            reloaded_data = load_languages()
            if user_id not in reloaded_data or reloaded_data[user_id] != selected_lang:
                # If validation fails, try to save again
                print(f"⚠️ Validation failed for user {user_id}, retrying save")
                save_languages()
                
            await interaction.response.send_message(
                f"🌍 Language set to `{selected_lang}`!", ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Error setting language for user {user_id}: {e}")
            await interaction.response.send_message(
                f"❌ Error saving language configuration. Please try again.", ephemeral=True
            )

class LanguageMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LanguageSelect())

# Periodic task to save configurations every 10 minutes
@tasks.loop(minutes=10)
async def periodic_save():
    try:
        if user_languages:  # Only save if there is data
            save_languages()
            print("🔄 Periodic save completed")
    except Exception as e:
        print(f"❌ Error in periodic save: {e}")

@periodic_save.before_loop
async def before_periodic_save():
    await bot.wait_until_ready()

# Events
@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    
    # Validate and show loaded configurations
    print(f"📊 Loaded configurations for {len(user_languages)} users")
    
    # Start periodic saving
    if not periodic_save.is_running():
        periodic_save.start()
        print("🔄 Periodic save task started")
    
    bot.add_view(LanguageMenu())

    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name="choose-language")
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

    # Prevent duplicate translations
    if (message.id, user_id) in translated_messages:
        return
    translated_messages.add((message.id, user_id))

    if user_id not in user_languages:
        channel = discord.utils.get(message.guild.text_channels, name="choose-language")
        if channel:
            try:
                await channel.send(f"{user.mention} ❗ Please select your language using the menu above.", delete_after=10)
            except:
                pass
        return

    if user.id == message.author.id:
        return  # Silently ignore, without notification

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

# Commands
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

# Execute
def run_bot():
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("❌ Token not found. Please set DISCORD_BOT_TOKEN.")
    else:
        bot.run(TOKEN)
