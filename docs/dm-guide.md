# Dungeon Master Guide

## Overview
The bot acts as an AI co-DM. It handles narration, dice rolls, NPC dialogue, and mechanical tracking while you focus on shaping the story.

You also have access to DM-only slash commands that players cannot use.

## Starting a Campaign
1. Create a session: `/session create [name]`.
2. Share the session name or ID with your players and have them use `/session join`.
3. Wait for players to create or bind their characters to the session.
4. Use `/game list` to see who has joined and their readiness.
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
- The dashboard shares the same database as the Discord bot, so changes are live immediately.

## Tips for Good Sessions
- The AI DM responds to player freeform text, so you do not need to script every interaction.
- Use `/dm narrate` to redirect the story if players go off-track.
- NPCs created with `/dm npc create` are persistent and can be re-encountered.
- The AI remembers party backstories, active quests, and current location when generating responses.
