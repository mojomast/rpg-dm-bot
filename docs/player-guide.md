# Player Guide

## Getting Started
1. Wait for the DM to create a campaign and invite players.
2. Use `/session join` with the session name or ID the DM gives you.
3. Create your character with `/character create` and choose a name, race, class, and backstory.
4. The DM will launch the campaign and you will receive a scene description.
5. Interact with the world by sending messages to the bot in the campaign channel with `@` mentions, or by using slash commands.
6. You can also continue your campaign from the web browser chat on the server's web dashboard URL.

## Your Character
- `/character sheet` - view your character sheet
- `/character levelup` - level up when you have enough XP
- `/character rest` - take a short rest or long rest to recover HP
- `/character switch` - switch characters if you have multiple characters in different campaigns

## Combat
Combat is turn-based and usually starts when the DM triggers an encounter or the party runs into one.

| Command | What it does |
| --- | --- |
| `/combat attack` | Attack a target |
| `/combat defend` | Take a defensive stance |
| `/combat spell` | Cast a spell |
| `/combat item` | Use an item |
| `/combat flee` | Try to escape |
| `/combat status` | View combat status |

The AI DM narrates combat actions, so just describe what your character wants to do.

## Spells & Abilities
Spellcasting classes like Mage, Cleric, Bard, Warlock, Paladin, and Ranger have cantrips and leveled spells.

- `/spell list` - see known spells
- `/spell learn` - learn a new spell appropriate to your level
- `/spell cast` - cast a spell, with a selection UI if you do not specify one
- `/spell slots` - see remaining spell slots
- `/spell info [spell name]` - get spell details

## Inventory & Items
- `/inventory view` - see your items
- `/inventory use [item]` - use a consumable
- `/inventory equip [item]` - equip an item
- `/inventory unequip [item]` - unequip an item
- `/inventory shop` - visit the in-game shop
- `/inventory give [item] [player]` - trade with a party member
- `/inventory transfer_gold [player] [amount]` - send gold to another player

## Quests
- `/quest list` - view available and active quests
- `/quest accept [quest]` - accept a quest
- `/quest info [quest]` - get details and objectives
- `/quest complete` - complete an objective
- `/quest abandon` - abandon a quest

## Dice Rolling
- `/roll dice [notation]` - for example `/roll dice 2d6+3`
- `/roll attack`
- `/roll save`
- `/roll skill`
- `/roll initiative`

## Talking to the Dungeon Master
- `@` mention the bot in the campaign channel with anything you want to say or do
- Use `/dm` for direct DM interactions, for example `/dm I search the room for hidden doors`
- Use `/action` for quick action buttons like Explore, Talk, Search, Rest, and Continue
- The bot only answers in the approved campaign channel

## Tips
- The DM is an AI, so describe your actions in natural language for best results.
- The bot tracks your character state, location, party, and quest progress automatically.
- If something seems wrong with your character stats, use `/character sheet` to verify.
