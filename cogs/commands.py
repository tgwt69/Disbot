"""
General commands cog for Discord AI Selfbot
Enhanced with 2025 features and better error handling
"""

import asyncio
import time
import logging
import psutil
import platform
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import discord
from discord.ext import commands

from utils.db import (
    add_channel, remove_channel, get_channels, 
    add_ignored_user, remove_ignored_user, get_ignored_users,
    get_user_stats, get_database_stats, cleanup_old_data
)
from utils.ai import get_ai_status, get_available_models, analyze_sentiment
from utils.error_notifications import webhook_log, test_webhook, get_error_stats
from utils.helpers import load_config, save_config, get_system_info

logger = logging.getLogger(__name__)

class GeneralCommands(commands.Cog):
    """Enhanced general commands for the selfbot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
    
    @commands.command(name="help", aliases=["h"])
    async def help_command(self, ctx):
        """Enhanced help command with categorized commands"""
        try:
            config = load_config()
            
            # Check if help is enabled for everyone or owner only
            if not config.get("bot", {}).get("help_command_enabled", True):
                if ctx.author.id != self.bot.state.owner_id:
                    return
            
            embed = discord.Embed(
                title="🤖 Discord AI Selfbot - Command Help",
                description="Enhanced 2025 Edition with Groq & OpenAI support",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            # Basic Commands
            basic_commands = [
                "`~help` - Show this help message",
                "`~ping` - Check bot latency and status",
                "`~status` - Show detailed bot status",
                "`~toggleactive [channel_id]` - Toggle bot activity in channel",
                "`~toggledm` - Toggle DM responses",
                "`~togglegc` - Toggle group chat responses"
            ]
            embed.add_field(
                name="📋 Basic Commands", 
                value="\n".join(basic_commands), 
                inline=False
            )
            
            # AI Commands
            ai_commands = [
                "`~models` - List available AI models",
                "`~analyze @user` - Analyze user's message history",
                "`~sentiment <text>` - Analyze text sentiment",
                "`~prompt [set/clear/view]` - Manage AI prompt"
            ]
            embed.add_field(
                name="🧠 AI Commands", 
                value="\n".join(ai_commands), 
                inline=False
            )
            
            # Management Commands
            mgmt_commands = [
                "`~ignore @user` - Ignore/unignore user",
                "`~wipe` - Clear conversation history",
                "`~pause` - Pause/unpause bot responses",
                "`~stats` - Show usage statistics"
            ]
            embed.add_field(
                name="⚙️ Management Commands", 
                value="\n".join(mgmt_commands), 
                inline=False
            )
            
            # Owner Only Commands
            if ctx.author.id == self.bot.state.owner_id:
                owner_commands = [
                    "`~reload` - Reload bot cogs",
                    "`~restart` - Restart the bot",
                    "`~shutdown` - Shutdown the bot",
                    "`~cleanup` - Clean old database records",
                    "`~testwh` - Test error webhook"
                ]
                embed.add_field(
                    name="👑 Owner Commands", 
                    value="\n".join(owner_commands), 
                    inline=False
                )
            
            embed.add_field(
                name="💡 Usage Tips",
                value="• Use the trigger word to start conversations\n"
                      "• Bot remembers conversation context\n"
                      "• Images are analyzed automatically\n"
                      "• Supports both Groq and OpenAI models",
                inline=False
            )
            
            embed.set_footer(
                text=f"Selfbot v3.0.0 | Uptime: {self.get_uptime()}"
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error displaying help. Check logs for details.")
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Enhanced ping command with detailed status"""
        try:
            start_time = time.time()
            
            # Calculate latencies
            websocket_latency = round(self.bot.latency * 1000, 2)
            
            # Create initial embed
            embed = discord.Embed(
                title="🏓 Pong!",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            # Send message and calculate edit latency
            message = await ctx.send(embed=embed)
            edit_time = time.time()
            edit_latency = round((edit_time - start_time) * 1000, 2)
            
            # Update embed with latencies
            embed.add_field(
                name="📡 WebSocket Latency",
                value=f"`{websocket_latency}ms`",
                inline=True
            )
            embed.add_field(
                name="⚡ Message Latency", 
                value=f"`{edit_latency}ms`",
                inline=True
            )
            embed.add_field(
                name="⏱️ Uptime",
                value=f"`{self.get_uptime()}`",
                inline=True
            )
            
            # Add status indicators
            ai_status = get_ai_status()
            status_indicators = []
            
            if ai_status.get("groq_available"):
                status_indicators.append("🟢 Groq")
            else:
                status_indicators.append("🔴 Groq")
                
            if ai_status.get("openai_available"):
                status_indicators.append("🟢 OpenAI")
            else:
                status_indicators.append("🔴 OpenAI")
            
            embed.add_field(
                name="🤖 AI Status",
                value=" | ".join(status_indicators),
                inline=False
            )
            
            # System info
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent(interval=1)
            
            embed.add_field(
                name="💻 System",
                value=f"CPU: `{cpu_usage}%` | RAM: `{memory_usage}%`",
                inline=True
            )
            embed.add_field(
                name="📊 Active Channels",
                value=f"`{len(self.bot.state.active_channels)}`",
                inline=True
            )
            
            # Update color based on latency
            if websocket_latency > 200:
                embed.color = 0xff0000  # Red
            elif websocket_latency > 100:
                embed.color = 0xffff00  # Yellow
            else:
                embed.color = 0x00ff00  # Green
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in ping command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error getting ping information.")
    
    @commands.command(name="status")
    async def status(self, ctx):
        """Detailed bot status information"""
        try:
            embed = discord.Embed(
                title="📊 Bot Status - Detailed Information",
                color=0x0099ff,
                timestamp=datetime.utcnow()
            )
            
            # Bot Information
            embed.add_field(
                name="🤖 Bot Info",
                value=f"**Version:** 3.0.0\n"
                      f"**Uptime:** {self.get_uptime()}\n"
                      f"**Owner:** <@{self.bot.state.owner_id}>\n"
                      f"**Paused:** {'Yes' if self.bot.state.paused else 'No'}",
                inline=True
            )
            
            # AI Status
            ai_status = get_ai_status()
            ai_info = []
            if ai_status.get("groq_available"):
                ai_info.append(f"🟢 **Groq:** {ai_status.get('groq_model', 'Unknown')}")
            else:
                ai_info.append("🔴 **Groq:** Unavailable")
                
            if ai_status.get("openai_available"):
                ai_info.append(f"🟢 **OpenAI:** {ai_status.get('openai_model', 'Unknown')}")
            else:
                ai_info.append("🔴 **OpenAI:** Unavailable")
            
            embed.add_field(
                name="🧠 AI Services",
                value="\n".join(ai_info),
                inline=True
            )
            
            # Channel Information
            active_channels = len(self.bot.state.active_channels)
            ignored_users = len(self.bot.state.ignore_users)
            
            embed.add_field(
                name="📡 Activity",
                value=f"**Active Channels:** {active_channels}\n"
                      f"**Ignored Users:** {ignored_users}\n"
                      f"**DMs Enabled:** {'Yes' if self.bot.state.allow_dm else 'No'}\n"
                      f"**Group Chats:** {'Yes' if self.bot.state.allow_gc else 'No'}",
                inline=True
            )
            
            # System Information
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            embed.add_field(
                name="💻 System Resources",
                value=f"**CPU Usage:** {psutil.cpu_percent()}%\n"
                      f"**Memory:** {memory.percent}% ({memory.used // 1024 // 1024}MB)\n"
                      f"**Disk:** {disk.percent}% used\n"
                      f"**Platform:** {platform.system()} {platform.release()}",
                inline=True
            )
            
            # Database Statistics
            db_stats = get_database_stats()
            embed.add_field(
                name="💾 Database",
                value=f"**Conversations:** {db_stats.get('conversation_records', 0)}\n"
                      f"**Tracked Users:** {db_stats.get('tracked_users', 0)}\n"
                      f"**Error Logs:** {db_stats.get('error_logs', 0)}\n"
                      f"**DB Size:** {self.format_bytes(db_stats.get('database_size', 0))}",
                inline=True
            )
            
            # Error Statistics
            error_stats = get_error_stats()
            embed.add_field(
                name="⚠️ Error Tracking",
                value=f"**Total Errors:** {error_stats.get('total_errors', 0)}\n"
                      f"**Recent (1h):** {error_stats.get('recent_errors', 0)}\n"
                      f"**Webhook:** {'✅' if error_stats.get('webhook_configured') else '❌'}\n"
                      f"**Error Types:** {error_stats.get('total_error_types', 0)}",
                inline=True
            )
            
            # Send as plain text since discord.py-self has different embed requirements
            status_text = f"""**📊 Bot Status - Detailed Information**

**🤖 Bot Info**
Version: 3.0.0
Uptime: {self.get_uptime()}
Owner: <@{self.bot.state.owner_id}>
Paused: {'Yes' if self.bot.state.paused else 'No'}

**🧠 AI Services**
{chr(10).join(ai_info)}

**📡 Activity**
Active Channels: {active_channels}
Ignored Users: {ignored_users}
DMs Enabled: {'Yes' if self.bot.state.allow_dm else 'No'}
Group Chats: {'Yes' if self.bot.state.allow_gc else 'No'}

**💻 System Resources**
CPU Usage: {psutil.cpu_percent()}%
Memory: {memory.percent}% ({memory.used // 1024 // 1024}MB)
Disk: {disk.percent}% used
Platform: {platform.system()} {platform.release()}

Use ~help for available commands"""
            await ctx.send(status_text)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error getting status information.")
    
    @commands.command(name="toggleactive", aliases=["toggle"])
    async def toggle_active(self, ctx, channel_id: Optional[int] = None):
        """Toggle bot activity in a channel"""
        try:
            target_channel_id = channel_id or ctx.channel.id
            
            if target_channel_id in self.bot.state.active_channels:
                # Remove channel silently
                if remove_channel(target_channel_id):
                    self.bot.state.active_channels.discard(target_channel_id)
                    # Add reaction to confirm without sending message
                    try:
                        await ctx.message.add_reaction("👎")
                    except:
                        pass
            else:
                # Add channel silently
                guild_id = ctx.guild.id if ctx.guild else None
                channel_name = ctx.channel.name if hasattr(ctx.channel, 'name') else "DM"
                
                if add_channel(target_channel_id, guild_id, channel_name, ctx.author.id):
                    self.bot.state.active_channels.add(target_channel_id)
                    # Add reaction to confirm without sending message
                    try:
                        await ctx.message.add_reaction("👍")
                    except:
                        pass
                    
        except Exception as e:
            logger.error(f"Error in toggle_active command: {e}")
            await webhook_log(ctx.message, e)
            # Silent failure - no error message sent
    
    @commands.command(name="toggledm")
    async def toggle_dm(self, ctx):
        """Toggle DM responses"""
        try:
            self.bot.state.allow_dm = not self.bot.state.allow_dm
            
            # Update config file
            config = load_config()
            config["bot"]["allow_dm"] = self.bot.state.allow_dm
            save_config(config)
            
            status = "enabled" if self.bot.state.allow_dm else "disabled"
            await ctx.send(f"✅ DM responses {status}")
            
        except Exception as e:
            logger.error(f"Error in toggle_dm command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error toggling DM setting.")
    
    @commands.command(name="togglegc")
    async def toggle_gc(self, ctx):
        """Toggle group chat responses"""
        try:
            self.bot.state.allow_gc = not self.bot.state.allow_gc
            
            # Update config file
            config = load_config()
            config["bot"]["allow_gc"] = self.bot.state.allow_gc
            save_config(config)
            
            status = "enabled" if self.bot.state.allow_gc else "disabled"
            await ctx.send(f"✅ Group chat responses {status}")
            
        except Exception as e:
            logger.error(f"Error in toggle_gc command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error toggling group chat setting.")
    
    @commands.command(name="ignore")
    async def ignore_user(self, ctx, user: Optional[discord.Member] = None):
        """Ignore or unignore a user"""
        try:
            if not user:
                await ctx.send("❌ Please mention a user to ignore/unignore")
                return
            
            if user.id == self.bot.state.owner_id:
                await ctx.send("❌ Cannot ignore the bot owner")
                return
            
            if user.id in self.bot.state.ignore_users:
                # Unignore user
                if remove_ignored_user(user.id):
                    self.bot.state.ignore_users.discard(user.id)
                    await ctx.send(f"✅ {user.mention} is no longer ignored")
                else:
                    await ctx.send("❌ Failed to unignore user")
            else:
                # Ignore user
                if add_ignored_user(user.id, str(user), "Manually ignored", ctx.author.id):
                    self.bot.state.ignore_users.add(user.id)
                    await ctx.send(f"✅ {user.mention} is now ignored")
                else:
                    await ctx.send("❌ Failed to ignore user")
                    
        except Exception as e:
            logger.error(f"Error in ignore command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error managing ignored users.")
    
    @commands.command(name="pause")
    async def pause_bot(self, ctx):
        """Pause or unpause bot responses"""
        try:
            self.bot.state.paused = not self.bot.state.paused
            status = "paused" if self.bot.state.paused else "resumed"
            emoji = "⏸️" if self.bot.state.paused else "▶️"
            
            await ctx.send(f"{emoji} Bot responses {status}")
            
        except Exception as e:
            logger.error(f"Error in pause command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error pausing/resuming bot.")
    
    @commands.command(name="wipe", aliases=["clear"])
    async def wipe_history(self, ctx, user: Optional[discord.Member] = None):
        """Clear conversation history"""
        try:
            if user:
                # Clear specific user's history
                if user.id in self.bot.state.message_history:
                    del self.bot.state.message_history[user.id]
                    await ctx.send(f"✅ Cleared conversation history for {user.mention}")
                else:
                    await ctx.send(f"❌ No conversation history found for {user.mention}")
            else:
                # Clear all history
                self.bot.state.message_history.clear()
                await ctx.send("✅ Cleared all conversation history")
                
        except Exception as e:
            logger.error(f"Error in wipe command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error clearing history.")
    
    @commands.command(name="models")
    async def list_models(self, ctx):
        """List available AI models"""
        try:
            models = await get_available_models()
            
            embed = discord.Embed(
                title="🤖 Available AI Models",
                color=0x0099ff,
                timestamp=datetime.utcnow()
            )
            
            # Groq models
            if models.get("groq"):
                groq_list = models["groq"][:10]  # Limit to first 10
                embed.add_field(
                    name="🚀 Groq Models (Fast & Free)",
                    value="```\n" + "\n".join(groq_list) + "```",
                    inline=False
                )
            
            # OpenAI models
            if models.get("openai"):
                openai_list = [m for m in models["openai"] if "gpt" in m.lower()][:5]
                embed.add_field(
                    name="🧠 OpenAI Models",
                    value="```\n" + "\n".join(openai_list) + "```",
                    inline=False
                )
            
            # Current configuration
            ai_status = get_ai_status()
            current_config = []
            if ai_status.get("groq_available"):
                current_config.append(f"**Groq:** {ai_status['groq_model']}")
            if ai_status.get("openai_available"):
                current_config.append(f"**OpenAI:** {ai_status['openai_model']}")
            
            if current_config:
                embed.add_field(
                    name="⚙️ Current Configuration",
                    value="\n".join(current_config),
                    inline=False
                )
            
            embed.set_footer(text="Models are automatically selected based on availability")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in models command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error retrieving model information.")
    
    @commands.command(name="analyze", aliases=["analyse"])
    async def analyze_user(self, ctx, user: Optional[discord.Member] = None):
        """Analyze a user's message patterns (for fun)"""
        try:
            if not user:
                await ctx.send("❌ Please mention a user to analyze")
                return
            
            if user.id == ctx.author.id:
                await ctx.send("🤔 Analyzing yourself? That's... interesting.")
                return
            
            # Get user statistics
            stats = get_user_stats(user.id)
            
            if not stats:
                await ctx.send(f"❌ No conversation data found for {user.mention}")
                return
            
            embed = discord.Embed(
                title=f"📊 User Analysis: {user.display_name}",
                description="*This is for entertainment purposes only and not scientifically accurate*",
                color=0x9932cc,
                timestamp=datetime.utcnow()
            )
            
            # Basic statistics
            embed.add_field(
                name="📈 Statistics",
                value=f"**Messages:** {stats['total_messages']}\n"
                      f"**Responses:** {stats['total_responses']}\n"
                      f"**Avg Response Time:** {stats['average_response_time']:.2f}s\n"
                      f"**First Seen:** {stats['first_interaction'][:10]}",
                inline=True
            )
            
            # Fun personality traits (generated randomly for entertainment)
            import random
            traits = [
                "🎭 Dramatic tendencies", "🧠 Deep thinker", "😄 Comedy enthusiast",
                "🎯 Goal-oriented", "🌟 Creative spirit", "🔍 Detail-focused",
                "💬 Social butterfly", "🎨 Artistic flair", "⚡ Quick wit",
                "🌙 Night owl", "☀️ Morning person", "🎵 Music lover"
            ]
            
            selected_traits = random.sample(traits, min(3, len(traits)))
            
            embed.add_field(
                name="🎭 Personality Traits",
                value="\n".join(f"• {trait}" for trait in selected_traits),
                inline=True
            )
            
            # Activity pattern
            last_seen = datetime.fromisoformat(stats['last_interaction'])
            days_ago = (datetime.now() - last_seen).days
            
            if days_ago == 0:
                activity = "🟢 Very Active"
            elif days_ago < 7:
                activity = "🟡 Moderately Active" 
            else:
                activity = "🔴 Less Active"
            
            embed.add_field(
                name="📅 Activity Pattern",
                value=f"**Status:** {activity}\n"
                      f"**Last Seen:** {days_ago} days ago\n"
                      f"**Preferred Topics:** {stats.get('preferred_topics', 'Various')}",
                inline=True
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text="🎪 This analysis is for entertainment only!")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in analyze command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error analyzing user.")
    
    @commands.command(name="sentiment")
    async def analyze_sentiment_command(self, ctx, *, text: str = None):
        """Analyze sentiment of provided text"""
        try:
            if not text:
                await ctx.send("❌ Please provide text to analyze")
                return
            
            if len(text) > 1000:
                await ctx.send("❌ Text too long (max 1000 characters)")
                return
            
            # Analyze sentiment
            result = await analyze_sentiment(text)
            
            sentiment = result.get("sentiment", "neutral").title()
            confidence = result.get("confidence", 0.0)
            explanation = result.get("explanation", "Analysis completed")
            
            # Choose emoji based on sentiment
            if sentiment.lower() == "positive":
                emoji = "😊"
                color = 0x00ff00
            elif sentiment.lower() == "negative":
                emoji = "😞"
                color = 0xff0000
            else:
                emoji = "😐"
                color = 0xffff00
            
            embed = discord.Embed(
                title=f"{emoji} Sentiment Analysis",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="📝 Text",
                value=f"```{text[:200]}{'...' if len(text) > 200 else ''}```",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Sentiment",
                value=f"**{sentiment}**",
                inline=True
            )
            
            embed.add_field(
                name="📊 Confidence",
                value=f"{confidence:.1%}",
                inline=True
            )
            
            embed.add_field(
                name="💡 Method",
                value=explanation,
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in sentiment command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error analyzing sentiment.")
    
    @commands.command(name="stats")
    async def show_stats(self, ctx):
        """Show bot usage statistics"""
        try:
            embed = discord.Embed(
                title="📊 Bot Usage Statistics",
                color=0x0099ff,
                timestamp=datetime.utcnow()
            )
            
            # Database stats
            db_stats = get_database_stats()
            embed.add_field(
                name="💾 Database",
                value=f"**Conversations:** {db_stats.get('conversation_records', 0):,}\n"
                      f"**Unique Users:** {db_stats.get('tracked_users', 0):,}\n"
                      f"**Active Channels:** {db_stats.get('active_channels', 0)}\n"
                      f"**Ignored Users:** {db_stats.get('ignored_users', 0)}",
                inline=True
            )
            
            # System stats
            uptime_seconds = time.time() - self.start_time
            embed.add_field(
                name="⏱️ Runtime",
                value=f"**Uptime:** {self.get_uptime()}\n"
                      f"**Memory Usage:** {psutil.virtual_memory().percent:.1f}%\n"
                      f"**CPU Usage:** {psutil.cpu_percent():.1f}%\n"
                      f"**Platform:** {platform.system()}",
                inline=True
            )
            
            # Error stats
            error_stats = get_error_stats()
            embed.add_field(
                name="⚠️ Error Tracking",
                value=f"**Total Errors:** {error_stats.get('total_errors', 0)}\n"
                      f"**Recent (1h):** {error_stats.get('recent_errors', 0)}\n"
                      f"**Error Types:** {error_stats.get('total_error_types', 0)}\n"
                      f"**Webhook:** {'✅' if error_stats.get('webhook_configured') else '❌'}",
                inline=True
            )
            
            # AI usage
            ai_status = get_ai_status()
            ai_services = []
            if ai_status.get("groq_available"):
                ai_services.append("🚀 Groq")
            if ai_status.get("openai_available"):
                ai_services.append("🧠 OpenAI")
            
            embed.add_field(
                name="🤖 AI Services",
                value="\n".join(ai_services) if ai_services else "❌ None available",
                inline=True
            )
            
            # Current session stats
            active_conversations = len(self.bot.state.active_conversations)
            message_queues = sum(len(q) for q in self.bot.state.message_queues.values())
            
            embed.add_field(
                name="📈 Current Session",
                value=f"**Active Conversations:** {active_conversations}\n"
                      f"**Queued Messages:** {message_queues}\n"
                      f"**Bot Status:** {'⏸️ Paused' if self.bot.state.paused else '▶️ Active'}\n"
                      f"**Latency:** {round(self.bot.latency * 1000)}ms",
                inline=True
            )
            
            embed.set_footer(text="Statistics are updated in real-time")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await webhook_log(ctx.message, e)
            await ctx.send("❌ Error retrieving statistics.")
    
    def get_uptime(self) -> str:
        """Get formatted uptime string"""
        uptime_seconds = int(time.time() - self.start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days: parts.append(f"{days}d")
        if hours: parts.append(f"{hours}h")
        if minutes: parts.append(f"{minutes}m")
        if seconds or not parts: parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(GeneralCommands(bot))

