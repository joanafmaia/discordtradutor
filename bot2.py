import discord
from discord.ext import commands, tasks
from deep_translator import GoogleTranslator
from collections import defaultdict, Counter
import os
import json
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Configure logging system
def setup_logging():
    """Set up logging configuration with file and console output."""
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create logger
    logger = logging.getLogger('discord_translator')
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler with rotation (max 10MB, keep 5 backup files)
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'bot.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logging
logger = setup_logging()
logger.info("🚀 Discord Translator Bot - Logging system initialized")
logger.info(f"📁 Log files will be stored in: logs/bot.log")

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
    '🇨🇳': 'zh-CN',
    '🇵🇱': 'pl',
    '🇹🇷': 'tr',
    '🏴': 'cy',
    '🇮🇩': 'id'
    # '🇯🇵': 'ja',
    # '🇰🇷': 'ko',
    # '🇸🇦': 'ar',
    # '🇷🇺': 'ru',
    # '🇮🇳': 'hi',
    # '🇳🇱': 'nl',
    # '🇻🇳': 'vi',
    # '🇹🇭': 'th',
    # '🇺🇦': 'uk',
    # '🇸🇪': 'sv'
}

# Language code to full name mapping
LANGUAGE_NAMES = {
    'en': 'English',
    'es': 'Español', 
    'pt': 'Português',
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'zh-CN': '中文',
    'pl': 'Polski',
    'tr': 'Türkçe',
    'cy': 'Cymraeg',
    'id': 'Bahasa Indonesia'
    # 'ja': '日本語',
    # 'ko': '한국어',
    # 'ar': 'العربية',
    # 'ru': 'Русский',
    # 'hi': 'हिन्दी',
    # 'nl': 'Nederlands',
    # 'vi': 'Tiếng Việt',
    # 'th': 'ไทย',
    # 'uk': 'Українська',
    # 'sv': 'Svenska'
}

LANGUAGE_FILE = "languages.json"

# Allowed server IDs - Add your server IDs here
# To get a server ID, use the /serverid command
ALLOWED_SERVERS = [
    1370614666002305166,  # EOS
    1372980735799201792,  # BLB
    1373791361551306822   # Joana's Server
]

# Set to True to enable server whitelist, False to allow all servers
ENABLE_SERVER_WHITELIST = True

def is_server_allowed(guild_id):
    """Check if a server is in the allowed list."""
    if not ENABLE_SERVER_WHITELIST:
        return True
    return guild_id in ALLOWED_SERVERS

def get_language_name(lang_code):
    """Get the full language name from language code."""
    return LANGUAGE_NAMES.get(lang_code, lang_code)

def get_user_language_status(user_id):
    """Get formatted language status message for a user."""
    user_id_str = str(user_id)
    if user_id_str in user_languages:
        current_lang = user_languages[user_id_str]
        current_lang_name = get_language_name(current_lang)
        return f"Your current language: **{current_lang_name}**"
    return "No language configured yet"

def load_languages():
    try:
        with open(LANGUAGE_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"✅ Loaded {len(data)} user language configurations")
            return data
    except FileNotFoundError:
        logger.warning(f"⚠️ File {LANGUAGE_FILE} not found, starting with empty configuration")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing {LANGUAGE_FILE}: {e}")
        logger.info("🔄 Creating backup and starting fresh")
        # Create backup of corrupted file
        try:
            os.rename(LANGUAGE_FILE, f"{LANGUAGE_FILE}.backup")
        except:
            pass
        return {}
    except Exception as e:
        logger.error(f"❌ Unexpected error loading languages: {e}")
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
            
        logger.info(f"✅ Saved {len(user_languages)} user configurations")
        
    except Exception as e:
        logger.error(f"❌ Error saving languages: {e}")
        # Try to restore backup if it exists
        temp_file = f"{LANGUAGE_FILE}.temp"
        if os.path.exists(temp_file):
            try:
                os.rename(temp_file, LANGUAGE_FILE)
                logger.info("🔄 Restored from backup")
            except:
                logger.error("❌ Failed to restore backup")
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
        # Use the LANGUAGE_NAMES constant to maintain consistency
        options = [
            discord.SelectOption(label=name, value=code) 
            for code, name in LANGUAGE_NAMES.items()
        ]
        super().__init__(
            custom_id="language_select",
            placeholder="Select your preferred language...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        selected_lang = self.values[0]
        
        # Check if user had a previous language configured
        previous_lang = user_languages.get(user_id)
        selected_lang_name = get_language_name(selected_lang)
        
        try:
            # Update in memory
            user_languages[user_id] = selected_lang
            
            # Save to file with validation
            save_languages()
            
            # Verify that it was saved correctly
            reloaded_data = load_languages()
            if user_id not in reloaded_data or reloaded_data[user_id] != selected_lang:
                # If validation fails, try to save again
                logger.warning(f"⚠️ Validation failed for user {user_id}, retrying save")
                save_languages()
            
            # Create response message based on whether user had previous configuration
            if previous_lang and previous_lang != selected_lang:
                previous_lang_name = get_language_name(previous_lang)
                message = f"🌍 Language changed from **{previous_lang_name}** to **{selected_lang_name}**!"
            elif previous_lang == selected_lang:
                message = f"🌍 Your language is already set to **{selected_lang_name}**!"
            else:
                message = f"🌍 Language set to **{selected_lang_name}**!"
                
            await interaction.response.send_message(message, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error setting language for user {user_id}: {e}")
            await interaction.response.send_message(
                f"❌ Error saving language configuration. Please try again.", ephemeral=True
            )

class LanguageMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LanguageSelect())

class ContextualLanguageMenu(discord.ui.View):
    """Language menu that shows user's current language status."""
    def __init__(self, user_id):
        super().__init__(timeout=60)  # 60 seconds timeout for personal menus
        self.user_id = user_id
        self.add_item(LanguageSelect())
    
    async def on_timeout(self):
        """Called when the view times out."""
        try:
            for item in self.children:
                item.disabled = True
        except:
            pass

# Periodic task to save configurations every 10 minutes
@tasks.loop(minutes=10)
async def periodic_save():
    try:
        if user_languages:  # Only save if there is data
            save_languages()
            logger.info("🔄 Periodic save completed")
    except Exception as e:
        logger.error(f"❌ Error in periodic save: {e}")

@periodic_save.before_loop
async def before_periodic_save():
    await bot.wait_until_ready()

# Events
@bot.event
async def on_ready():
    logger.info(f"✅ Bot connected as {bot.user}")
    
    # Validate and show loaded configurations
    logger.info(f"📊 Loaded configurations for {len(user_languages)} users")
    
    # Log server whitelist status
    if ENABLE_SERVER_WHITELIST:
        logger.info(f"🔒 Server whitelist ENABLED - {len(ALLOWED_SERVERS)} servers allowed")
        logger.info(f"📋 Allowed server IDs: {ALLOWED_SERVERS}")
    else:
        logger.info("🌐 Server whitelist DISABLED - Bot will work in all servers")
    
    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synced {len(synced)} slash command(s) with Discord")
    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")
    
    # Start periodic saving
    if not periodic_save.is_running():
        periodic_save.start()
        logger.info("🔄 Periodic save task started")
    
    bot.add_view(LanguageMenu())

    for guild in bot.guilds:
        # Only setup channels in allowed servers
        if not is_server_allowed(guild.id):
            logger.warning(f"⚠️ Skipping setup for unauthorized server: {guild.name} (ID: {guild.id})")
            continue
            
        channel = discord.utils.get(guild.text_channels, name="choose-language")
        if channel:
            pinned = await channel.pins()
            for msg in pinned:
                if msg.author == bot.user and msg.content.startswith("🌐"):
                    break
            else:
                embed = discord.Embed(
                    title="🌐 Language Configuration",
                    description=(
                        "**Select your preferred language using the dropdown below:**\n\n"
                        "• This will set your default language for translations\n"
                        "• You can change it anytime by using this menu\n"
                        "• Use `/language` to check your current setting"
                    ),
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Your language setting is saved automatically")
                sent = await channel.send(embed=embed, view=LanguageMenu())
                await sent.pin()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check if server is allowed
    if message.guild and not is_server_allowed(message.guild.id):
        return

    await bot.process_commands(message)

    try:
        if not message.webhook_id:
            await message.add_reaction("🌍")
    except Exception as e:
        logger.error(f"[Reaction error] {e}")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if str(reaction.emoji) != "🌍":
        return

    message = reaction.message
    
    # Check if server is allowed
    if message.guild and not is_server_allowed(message.guild.id):
        return
    
    user_id = str(user.id)

    # Prevent duplicate translations
    if (message.id, user_id) in translated_messages:
        return
    translated_messages.add((message.id, user_id))

    if user_id not in user_languages:
        channel = discord.utils.get(message.guild.text_channels, name="choose-language")
        if channel:
            try:
                user_status = get_user_language_status(user.id)
                await channel.send(
                    f"{user.mention} ❗ **Please select your language**\n"
                    f"📊 Status: {user_status}\n"
                    f"👆 Use the menu above to configure your preferred language.",
                    delete_after=15
                )
            except:
                pass
        return

    if user.id == message.author.id:
        return  # Silently ignore, without notification

    lang = user_languages[user_id]

    try:
        translated = GoogleTranslator(source='auto', target=lang).translate(message.content)
    except Exception as e:
        logger.error(f"[Translation error] {e}")
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
        logger.error(f"[Send/delete error] {e}")

    translation_stats["total"] += 1
    translation_stats["per_user"][user.id] += 1
    translation_stats["per_language"][lang] += 1
    
    # Log translation activity
    logger.info(f"🔄 Translation completed: {user.display_name} ({user.id}) -> {lang} in {message.guild.name} #{message.channel.name}")

# Commands
@bot.hybrid_command(name="stats", description="Show translation statistics")
async def stats(ctx):
    # Check if server is allowed
    if ctx.guild and not is_server_allowed(ctx.guild.id):
        await ctx.send("❌ This bot is not authorized to work in this server.", ephemeral=True)
        return
    
    total = translation_stats["total"]
    users = len(translation_stats["per_user"])
    top_langs = translation_stats["per_language"].most_common(5)

    embed = discord.Embed(title="📊 Translation Stats", color=discord.Color.green())
    embed.add_field(name="Total translations", value=str(total), inline=False)
    embed.add_field(name="Users translated", value=str(users), inline=False)
    embed.add_field(name="Top languages", value="\n".join([f"{l} - {c}" for l, c in top_langs]) or "None yet.")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="language", description="Check or change your language setting")
async def language_cmd(ctx):
    # Check if server is allowed
    if ctx.guild and not is_server_allowed(ctx.guild.id):
        await ctx.send("❌ This bot is not authorized to work in this server.", ephemeral=True)
        return
    
    user_id = str(ctx.author.id)
    
    embed = discord.Embed(title="🌍 Your Language Configuration", color=discord.Color.blue())
    
    if user_id in user_languages:
        current_lang = user_languages[user_id]
        current_lang_name = get_language_name(current_lang)
        
        embed.add_field(
            name="Current Language",
            value=f"**{current_lang_name}** (`{current_lang}`)",
            inline=False
        )
        embed.add_field(
            name="How to change",
            value="Use the dropdown menu in #choose-language",
            inline=False
        )
        embed.set_footer(text="Language setting saved ✅")
    else:
        embed.add_field(
            name="Status",
            value="❌ No language configured yet",
            inline=False
        )
        embed.add_field(
            name="Next steps",
            value="Visit #choose-language to select your preferred language",
            inline=False
        )
        embed.set_footer(text="Translation features require language configuration")
    
    await ctx.send(embed=embed, ephemeral=True)

@bot.hybrid_command(name="logs", description="Test logging system (Admin only)")
async def logs_test(ctx):
    """Test command to verify logging system is working."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ This command is for administrators only.", ephemeral=True)
        return
    
    logger.info(f"🧪 Log test initiated by {ctx.author.display_name} ({ctx.author.id})")
    logger.warning("⚠️ This is a test warning message")
    logger.error("❌ This is a test error message")
    
    await ctx.send("🧪 Log test completed! Check the logs/bot.log file and console output.", ephemeral=True)

@bot.hybrid_command(name="serverid", description="Get the current server ID (Admin only)")
async def serverid(ctx):
    """Get the server ID - useful for configuring the whitelist."""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.", ephemeral=True)
        return
    
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ This command is for administrators only.", ephemeral=True)
        return
    
    embed = discord.Embed(title="🆔 Server Information", color=discord.Color.blue())
    embed.add_field(name="Server Name", value=ctx.guild.name, inline=False)
    embed.add_field(name="Server ID", value=f"`{ctx.guild.id}`", inline=False)
    
    is_allowed = is_server_allowed(ctx.guild.id)
    status = "✅ Authorized" if is_allowed else "❌ Not Authorized"
    embed.add_field(name="Status", value=status, inline=False)
    
    if ENABLE_SERVER_WHITELIST:
        embed.add_field(
            name="Whitelist Status",
            value=f"🔒 Enabled ({len(ALLOWED_SERVERS)} servers allowed)",
            inline=False
        )
    else:
        embed.add_field(
            name="Whitelist Status",
            value="🌐 Disabled (all servers allowed)",
            inline=False
        )
    
    embed.set_footer(text="Copy the Server ID to add it to ALLOWED_SERVERS in bot2.py")
    
    await ctx.send(embed=embed, ephemeral=True)
    logger.info(f"📋 Server ID requested by {ctx.author.display_name} in {ctx.guild.name} (ID: {ctx.guild.id})")

@bot.hybrid_command(name="sync", description="Sync bot commands with Discord (Owner only)")
async def sync_commands(ctx):
    """Manually sync slash commands with Discord."""
    if ctx.author.id != ctx.guild.owner_id and not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ This command is for server administrators only.", ephemeral=True)
        return
    
    try:
        await ctx.defer(ephemeral=True)
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Successfully synced {len(synced)} command(s) with Discord!", ephemeral=True)
        logger.info(f"🔄 Commands manually synced by {ctx.author.display_name} in {ctx.guild.name}")
    except Exception as e:
        await ctx.send(f"❌ Error syncing commands: {e}", ephemeral=True)
        logger.error(f"❌ Error syncing commands: {e}")

# Execute
def run_bot():
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        logger.error("❌ Token not found. Please set DISCORD_BOT_TOKEN.")
    else:
        bot.run(TOKEN)
