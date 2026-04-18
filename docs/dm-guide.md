# Dungeon Master Guide

## Overview
The bot acts as an AI co-DM. It handles narration, dice rolls, NPC dialogue, and mechanical tracking while you focus on shaping the story.

You also have access to DM-only slash commands that players cannot use.

## Starting a Campaign
1. Create a session: `/session create [name]`.
2. Share the session name or ID with your players and have them use `/session join`.
3. Wait for players to create or bind their characters to the session.
4. Use `/session` management commands to review the active session state.
5. When ready, launch the campaign with `/session start`.
6. Optionally run `/dm narrate` to set the opening scene manually.

## During a Session
- `/dm narrate [text]` - inject custom narration or set the scene
- `/dm npc create [name]` - create a new NPC on the fly
- `/dm spawn [enemy type]` - spawn enemies to trigger combat
- `/dm reward [player]` - grant items, gold, or XP to a player
- `/dm quest create` - create a quest
- `/dm quest edit [quest]` - edit an existing quest
- `/check [player] [skill]` - force a skill check for a player

## World State Commands
- `/world scene-set [description]` - update the active session's current scene note
- `/world location-move [location]` - move the party using canonical location traversal rules
- `/world location-reveal [location]` - reveal a hidden location to players
- `/world npc-reveal [npc]` - mark an NPC as encountered and visible to players
- `/world faction-rep [faction] [character] [change]` - adjust character reputation with a faction

These commands are `guild_only` and only work for the session DM or a server administrator.

## Managing Quests
- Create quests before or during sessions with `/dm quest create`.
- Quests have stages, and the AI DM automatically advances them based on player actions.
- You can manually set quest state via the web dashboard.

## Pausing and Resuming
- `/session end` pauses the campaign and saves progress.
- `/session start` with the same session resumes exactly where you left off.
- Players can also continue between sessions via browser chat.

## The Web Dashboard
- The dashboard URL is set by your operator.
- Use it to edit NPCs, manage quests, view character sheets, build the world map, and edit game data.
- Use `Campaign Studio` as the main DM workspace for:
  - campaign overview and current scene
  - location tree and reveal controls
  - cast review and NPC reveal
  - faction members and character reputation
  - storylines, plot points, and quest tracking
  - session narration and session-zero generation
- The dashboard shares the same database as the Discord bot, so changes are live immediately.

## Browser Chat
- Players can use browser chat with their session characters.
- If the browser identity belongs to the session DM, the same page exposes `DM` mode.
- DM mode does not require a selected character and sends direct DM directives to the model.
- The `Send as Narration` action turns the latest DM response into polished player-facing narration and also feeds the Campaign Studio narration panel.

## Tips for Good Sessions
- The AI DM responds to player freeform text, so you do not need to script every interaction.
- Use `/dm narrate` to redirect the story if players go off-track.
- Use `/world location-reveal` and `/world npc-reveal` to control discovery pacing instead of editing visibility ad hoc.
- NPCs created with `/dm npc create` are persistent and can be re-encountered.
- The AI remembers party backstories, active quests, and current location when generating responses.
