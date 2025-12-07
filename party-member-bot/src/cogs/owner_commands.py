"""
Party Member Bot - Owner Commands Cog
Commands that can only be used by the bot owner via DMs
"""

import discord
from discord.ext import commands
import logging
import json
from typing import Optional
from datetime import datetime
import os
import aiohttp
import time
import uuid

logger = logging.getLogger('party_member.owner')


class OwnerCommands(commands.Cog):
    """Commands for the bot owner to configure and control the bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def is_owner(self, user_id: int) -> bool:
        """Check if a user is the bot owner"""
        return self.bot.owner_id_config and user_id == self.bot.owner_id_config
    
    @commands.command(name='create')
    async def create_character(self, ctx: commands.Context):
        """Start the character creation interview"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            await ctx.send("❌ Only the bot owner can use this command.")
            return
        
        interview_cog = self.bot.get_cog('Interview')
        if interview_cog:
            await interview_cog.start_interview(ctx)
        else:
            await ctx.send("❌ Interview system not available.")
    
    @commands.command(name='cancel')
    async def cancel_interview(self, ctx: commands.Context):
        """Cancel the current character creation interview"""
        if not isinstance(ctx.channel, discord.DMChannel):
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        interview_cog = self.bot.get_cog('Interview')
        if interview_cog:
            interview_cog.end_session(ctx.author.id)
            await ctx.send("✅ Interview cancelled.")
    
    @commands.command(name='status')
    async def show_status(self, ctx: commands.Context):
        """Show the bot's current status"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        char = self.bot.character_data
        
        embed = discord.Embed(
            title="🤖 Party Member Bot Status",
            color=discord.Color.blue()
        )
        
        # Bot info
        embed.add_field(
            name="🔧 Bot Info",
            value=f"**Name:** {self.bot.user.name}\n"
                  f"**ID:** {self.bot.user.id}\n"
                  f"**Servers:** {len(self.bot.guilds)}",
            inline=False
        )
        
        # Character info
        if char:
            embed.add_field(
                name="📜 Character",
                value=f"**Name:** {char.get('name', 'Unknown')}\n"
                      f"**Race/Class:** {char.get('race', '?')} {char.get('class', '?')}\n"
                      f"**Level:** {char.get('level', 1)}\n"
                      f"**Play Style:** {char.get('play_style', 'balanced').title()}",
                inline=False
            )
        else:
            embed.add_field(
                name="📜 Character",
                value="❌ No character configured\nUse `!pm create` to create one!",
                inline=False
            )
        
        # Active sessions
        active_channels = list(self.bot.active_sessions.keys())
        if active_channels:
            channels_str = "\n".join([f"<#{c}>" for c in active_channels])
            embed.add_field(
                name="🎮 Active Sessions",
                value=channels_str,
                inline=False
            )
        else:
            embed.add_field(
                name="🎮 Active Sessions",
                value="Not in any sessions\nUse `!pm join #channel` to join one!",
                inline=False
            )
        
        # Auto-play status
        autoplay_channels = [c for c, enabled in self.bot.auto_play_mode.items() if enabled]
        if autoplay_channels:
            embed.add_field(
                name="🤖 Auto-Play Enabled",
                value="\n".join([f"<#{c}>" for c in autoplay_channels]),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='join')
    async def join_session(self, ctx: commands.Context, channel: discord.TextChannel):
        """Join a game session in a channel"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        # Check if bot can access the channel
        if not channel.permissions_for(channel.guild.me).send_messages:
            await ctx.send(f"❌ I don't have permission to send messages in {channel.mention}!")
            return
        
        self.bot.active_sessions[channel.id] = {
            'guild_id': channel.guild.id,
            'guild_name': channel.guild.name,
            'channel_name': channel.name,
            'joined_at': datetime.utcnow().isoformat()
        }
        
        await ctx.send(f"✅ Joined session in {channel.mention}!")
        
        # Announce arrival in channel
        char_name = self.bot.character_data.get('name', 'Adventurer')
        await channel.send(f"*{char_name} enters the scene, ready for adventure!*")
    
    @commands.command(name='leave')
    async def leave_session(self, ctx: commands.Context, channel: discord.TextChannel):
        """Leave a game session"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        if channel.id not in self.bot.active_sessions:
            await ctx.send(f"❌ Not currently in a session in {channel.mention}!")
            return
        
        del self.bot.active_sessions[channel.id]
        
        # Disable auto-play for this channel too
        if channel.id in self.bot.auto_play_mode:
            del self.bot.auto_play_mode[channel.id]
        
        await ctx.send(f"✅ Left session in {channel.mention}!")
        
        # Announce departure in channel
        char_name = self.bot.character_data.get('name', 'Adventurer')
        await channel.send(f"*{char_name} departs, waving farewell.*")
    
    @commands.command(name='autoplay')
    async def toggle_autoplay(self, ctx: commands.Context, state: str, channel: Optional[discord.TextChannel] = None):
        """Toggle auto-play mode for a channel"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        state_lower = state.lower()
        if state_lower not in ['on', 'off', 'true', 'false', '1', '0']:
            await ctx.send("❌ Usage: `!pm autoplay on/off [#channel]`")
            return
        
        enabled = state_lower in ['on', 'true', '1']
        
        if channel:
            # Set for specific channel
            if channel.id not in self.bot.active_sessions:
                await ctx.send(f"❌ Not in a session in {channel.mention}! Join first with `!pm join {channel.mention}`")
                return
            
            self.bot.auto_play_mode[channel.id] = enabled
            status = "enabled" if enabled else "disabled"
            await ctx.send(f"✅ Auto-play {status} for {channel.mention}!")
        else:
            # Set for all active sessions
            for channel_id in self.bot.active_sessions.keys():
                self.bot.auto_play_mode[channel_id] = enabled
            
            status = "enabled" if enabled else "disabled"
            await ctx.send(f"✅ Auto-play {status} for all active sessions!")
    
    @commands.command(name='say')
    async def say_as_character(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        """Send a message as the character in a channel"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        if channel.id not in self.bot.active_sessions:
            await ctx.send(f"❌ Not in a session in {channel.mention}!")
            return
        
        gameplay_cog = self.bot.get_cog('Gameplay')
        if gameplay_cog:
            await gameplay_cog.send_character_message(channel, message)
            await ctx.send(f"✅ Message sent to {channel.mention}!")
        else:
            await channel.send(message)
            await ctx.send(f"✅ Message sent to {channel.mention}!")
    
    @commands.command(name='do')
    async def do_action(self, ctx: commands.Context, channel: discord.TextChannel, *, action: str):
        """Perform an action as the character"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        if channel.id not in self.bot.active_sessions:
            await ctx.send(f"❌ Not in a session in {channel.mention}!")
            return
        
        char_name = self.bot.character_data.get('name', 'Adventurer')
        formatted = f"*{char_name} {action}*"
        
        await channel.send(formatted)
        await ctx.send(f"✅ Action performed in {channel.mention}!")
    
    @commands.command(name='register')
    async def register_character(self, ctx: commands.Context):
        """Register the character with the RPG DM bot (sends /character create command)"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        char = self.bot.character_data
        if not char:
            await ctx.send("❌ No character configured! Use `!pm create` first.")
            return
        
        guild_id = char.get('guild_id')
        if not guild_id:
            await ctx.send("❌ No server configured for this character. Run `!pm create` again.")
            return
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send("❌ Bot is not in the configured server!")
            return
        
        # Find a channel to register in
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="📝 Manual Registration Required",
                    description=f"To register **{char.get('name')}** with the RPG DM bot, "
                               f"you need to run the character creation command manually.\n\n"
                               f"Go to {channel.mention} and use:\n"
                               f"`/character create race:{char.get('race', 'human').lower()} "
                               f"char_class:{char.get('class', 'warrior').lower()}`\n\n"
                               f"Then fill in:\n"
                               f"• **Name:** {char.get('name', 'Adventurer')}\n"
                               f"• **Backstory:** {char.get('backstory', '')[:100] or 'Optional'}",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return
        
        await ctx.send("❌ Couldn't find a channel to register in!")

    @commands.command(name='register-auto')
    async def register_character_auto(self, ctx: commands.Context):
        """Attempt to automatically invoke the RPG DM bot's `/character create` command.

        This is a best-effort, opt-in feature. It will try to discover the RPG DM bot's
        application command in the configured guild and post an interaction to invoke it
        with the saved character data.
        """
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return

        if not self.is_owner(ctx.author.id):
            return

        char = self.bot.character_data
        if not char:
            await ctx.send("❌ No character configured! Use `!pm create` first.")
            return

        guild_id = char.get('guild_id')
        if not guild_id:
            await ctx.send("❌ No server configured for this character. Run `!pm create` again.")
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send("❌ Bot is not in the configured server!")
            return

        # Find a channel to register in
        target_channel = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                target_channel = channel
                break

        if not target_channel:
            await ctx.send("❌ Couldn't find a channel to register in!")
            return

        dm_bot_id = self.bot.dm_bot_id
        if not dm_bot_id:
            await ctx.send("❌ `DM_BOT_ID` not configured. Set DM_BOT_ID in your .env to the RPG DM bot's user id.")
            return

        # Use the DM bot id as the application id (best-effort)
        app_id = str(dm_bot_id)

        # Prefer an explicit DM bot token if provided (safer for cross-application calls).
        # If you own both bots, set DM_BOT_TOKEN in the party-member-bot .env to the DM bot's token.
        token = os.getenv('DM_BOT_TOKEN') or os.getenv('DISCORD_TOKEN')
        if not token:
            await ctx.send("❌ Server token not available (set `DM_BOT_TOKEN` or `DISCORD_TOKEN`). Cannot perform auto-registration.")
            return

        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                # Discover guild application commands for the DM bot
                url = f'https://discord.com/api/v10/applications/{app_id}/guilds/{guild_id}/commands'
                async with session.get(url) as resp:
                    if resp.status == 403:
                        await ctx.send("❌ Failed to fetch commands from target bot (403 Forbidden).\n" \
                                       "Possible fixes: ensure `DM_BOT_TOKEN` is set in `.env` to the DM bot's token,\n" \
                                       "or use the manual `!pm register` flow. If you set `DM_BOT_TOKEN`, restart the bot and try again.")
                        return
                    if resp.status != 200:
                        await ctx.send(f"❌ Failed to fetch commands from target bot (status {resp.status}).")
                        return
                    commands_list = await resp.json()

                # Find a command named 'character' or similar
                cmd = None
                for c in commands_list:
                    if c.get('name', '').lower().startswith('character'):
                        cmd = c
                        break

                # If we didn't find it, try a fallback: resolve the application's real id
                # via /oauth2/applications/@me (requires using the DM bot token) and retry
                if not cmd:
                    try:
                        me_url = 'https://discord.com/api/v10/oauth2/applications/@me'
                        async with session.get(me_url) as me_resp:
                            if me_resp.status == 200:
                                app_json = await me_resp.json()
                                real_app_id = str(app_json.get('id'))
                                # If it differs, try fetching guild commands for the real app id
                                if real_app_id and real_app_id != app_id:
                                    app_id = real_app_id
                                    retry_url = f'https://discord.com/api/v10/applications/{app_id}/guilds/{guild_id}/commands'
                                    async with session.get(retry_url) as r2:
                                        if r2.status == 200:
                                            commands_list = await r2.json()
                                            for c in commands_list:
                                                if c.get('name', '').lower().startswith('character'):
                                                    cmd = c
                                                    break
                    except Exception:
                        # ignore and continue to try global commands below
                        cmd = None

                # If still not found in guild commands, try global commands for the app
                if not cmd:
                    try:
                        global_url = f'https://discord.com/api/v10/applications/{app_id}/commands'
                        async with session.get(global_url) as gresp:
                            if gresp.status == 200:
                                gcmds = await gresp.json()
                                for c in gcmds:
                                    if c.get('name', '').lower().startswith('character'):
                                        cmd = c
                                        break
                    except Exception:
                        cmd = None

                if not cmd:
                    await ctx.send("❌ Couldn't find a `character` command on the target bot.\n" \
                                   "I attempted guild and global command listings and also tried resolving the bot's application id via `/oauth2/applications/@me`.\n" \
                                   "Make sure `DM_BOT_TOKEN` is set and that the token belongs to the RPG DM bot, or provide the DM bot's Application ID (not the user id).")
                    return

                command_id = cmd['id']
                command_name = cmd['name']

                # Build options based on known fields. Prefer nested subcommand usage
                race_val = (char.get('race') or '').lower()
                class_val = (char.get('class') or char.get('char_class') or '').lower()

                options = []

                # Some application commands use subcommands (type 1). The DM bot's
                # `/character` command defines a subcommand `create` with inner options
                # for `race` and `char_class`. If we detect that shape, build a nested
                # options structure like: { name: 'create', type:1, options: [ {name:'race', value:...}, ... ] }
                found_subcommand = None
                for top_opt in cmd.get('options', []) or []:
                    if top_opt.get('type') == 1 and top_opt.get('name', '').lower() == 'create':
                        found_subcommand = top_opt
                        break

                if found_subcommand:
                    inner_opts = []
                    for inner in found_subcommand.get('options', []) or []:
                        in_name = inner.get('name', '').lower()
                        # Only include values we actually have in character data and that match expected types
                        if in_name == 'race' and race_val:
                            # Try to match to one of the choice values if present
                            choices = {c.get('value', '').lower(): True for c in inner.get('choices', [])}
                            chosen = race_val
                            if choices and chosen not in choices:
                                # fallback: try to match by name (case-insensitive)
                                for c in inner.get('choices', []):
                                    if c.get('name', '').lower() == race_val:
                                        chosen = c.get('value')
                                        break
                            inner_opts.append({'name': in_name, 'type': 3, 'value': chosen})
                        if in_name in ('char_class', 'class', 'charclass') and class_val:
                            choices = {c.get('value', '').lower(): True for c in inner.get('choices', [])}
                            chosen = class_val
                            if choices and chosen not in choices:
                                for c in inner.get('choices', []):
                                    if c.get('name', '').lower() == class_val:
                                        chosen = c.get('value')
                                        break
                            inner_opts.append({'name': in_name, 'type': 3, 'value': chosen})
                        if in_name in ('name',) and char.get('name'):
                            inner_opts.append({'name': in_name, 'type': 3, 'value': char.get('name')})
                        if in_name in ('backstory', 'story', 'description') and char.get('backstory'):
                            inner_opts.append({'name': in_name, 'type': 3, 'value': char.get('backstory')})

                    if inner_opts:
                        options.append({'type': 1, 'name': 'create', 'options': inner_opts})
                else:
                    # Fallback: flat options (older or different command shapes)
                    for opt in cmd.get('options', []) or []:
                        opt_name = opt.get('name', '').lower()
                        if opt_name in ['race'] and race_val:
                            options.append({'name': 'race', 'type': 3, 'value': race_val})
                        if opt_name in ['char_class', 'class', 'charclass'] and class_val:
                            options.append({'name': opt_name, 'type': 3, 'value': class_val})
                        if opt_name in ['name'] and char.get('name'):
                            options.append({'name': 'name', 'type': 3, 'value': char.get('name')})
                        if opt_name in ['backstory', 'story', 'description'] and char.get('backstory'):
                            options.append({'name': opt_name, 'type': 3, 'value': char.get('backstory')})

                # Build interaction payload (type 2 = application command)
                interaction = {
                    'type': 2,
                    'application_id': app_id,
                    'guild_id': str(guild_id),
                    'channel_id': str(target_channel.id),
                    'session_id': str(uuid.uuid4()),
                    'data': {
                        'id': command_id,
                        'name': command_name,
                        'type': 1,
                        'options': options
                    }
                }

                interact_url = 'https://discord.com/api/v10/interactions'
                async with session.post(interact_url, json=interaction) as r:
                    if r.status in (200, 204):
                        await ctx.send(f"✅ Auto-registration sent to {target_channel.mention}. Check the channel for the DM bot's response.")
                        return
                    else:
                        text = await r.text()
                        await ctx.send(f"❌ Auto-registration failed (status {r.status}): {text}")
                        return

            except Exception as e:
                await ctx.send(f"❌ Exception during auto-registration: {e}")
                return
    
    @commands.command(name='character')
    async def show_character(self, ctx: commands.Context):
        """Show detailed character information"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        char = self.bot.character_data
        if not char:
            await ctx.send("❌ No character configured! Use `!pm create` to create one.")
            return
        
        stats = char.get('stats', {})
        
        embed = discord.Embed(
            title=f"📜 {char.get('name', 'Unknown')}",
            description=f"Level {char.get('level', 1)} {char.get('race', '?')} {char.get('class', '?')}",
            color=discord.Color.gold()
        )
        
        if stats:
            embed.add_field(
                name="📊 Stats",
                value=f"**STR:** {stats.get('strength', 10)} | "
                      f"**DEX:** {stats.get('dexterity', 10)} | "
                      f"**CON:** {stats.get('constitution', 10)}\n"
                      f"**INT:** {stats.get('intelligence', 10)} | "
                      f"**WIS:** {stats.get('wisdom', 10)} | "
                      f"**CHA:** {stats.get('charisma', 10)}",
                inline=False
            )
        
        embed.add_field(
            name="⚔️ Play Style",
            value=char.get('play_style', 'balanced').title(),
            inline=True
        )
        
        embed.add_field(
            name="🏰 Server",
            value=char.get('guild_name', 'Unknown'),
            inline=True
        )
        
        if char.get('backstory'):
            embed.add_field(
                name="📖 Backstory",
                value=char['backstory'][:1000] + ('...' if len(char['backstory']) > 1000 else ''),
                inline=False
            )
        
        if char.get('personality'):
            embed.add_field(
                name="🎭 Personality",
                value=char['personality'][:500],
                inline=False
            )
        
        if char.get('created_at'):
            embed.set_footer(text=f"Created: {char['created_at']}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='edit')
    async def edit_character(self, ctx: commands.Context, field: str, *, value: str):
        """Edit a character field (name, backstory, personality, play_style)"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        char = self.bot.character_data
        if not char:
            await ctx.send("❌ No character configured! Use `!pm create` to create one.")
            return
        
        valid_fields = ['name', 'backstory', 'personality', 'play_style']
        field_lower = field.lower()
        
        if field_lower not in valid_fields:
            await ctx.send(f"❌ Invalid field. Valid fields: {', '.join(valid_fields)}")
            return
        
        if field_lower == 'play_style':
            valid_styles = ['aggressive', 'defensive', 'balanced', 'cautious', 'reckless']
            if value.lower() not in valid_styles:
                await ctx.send(f"❌ Invalid play style. Valid: {', '.join(valid_styles)}")
                return
            value = value.lower()
        
        self.bot.character_data[field_lower] = value
        await self.bot.save_character_data()
        
        await ctx.send(f"✅ Updated **{field}** to: {value[:100]}{'...' if len(value) > 100 else ''}")
        
        # Update presence if name changed
        if field_lower == 'name':
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name=f"as {value} | DM me to configure"
            )
            await self.bot.change_presence(activity=activity)
    
    @commands.command(name='help')
    async def show_help(self, ctx: commands.Context):
        """Show all available commands"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("❌ This command can only be used in DMs!")
            return
        
        if not self.is_owner(ctx.author.id):
            return
        
        embed = discord.Embed(
            title="🤖 Party Member Bot Commands",
            description="All commands use the `!pm` prefix and must be sent via DM.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📜 Character Management",
            value="• `!pm create` - Start character creation interview\n"
                  "• `!pm character` - View character details\n"
                  "• `!pm edit <field> <value>` - Edit character field\n"
                  "• `!pm register` - Get instructions to register with DM bot",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Session Management",
            value="• `!pm join #channel` - Join a game session\n"
                  "• `!pm leave #channel` - Leave a game session\n"
                  "• `!pm autoplay on/off [#channel]` - Toggle auto-play",
            inline=False
        )
        
        embed.add_field(
            name="💬 Communication",
            value="• `!pm say #channel <message>` - Speak as character\n"
                  "• `!pm do #channel <action>` - Perform an action",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Information",
            value="• `!pm status` - View bot status\n"
                  "• `!pm help` - Show this help message",
            inline=False
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(OwnerCommands(bot))
