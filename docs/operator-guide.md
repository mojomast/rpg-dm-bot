# Operator / Self-Hosting Guide

## Prerequisites
- Python 3.10+
- A Discord application and bot token: https://discord.com/developers/applications
- An LLM API key: either OpenRouter (https://openrouter.ai) or Requesty (https://requesty.ai)
- Node.js 18+ if you plan to build or modify the frontend

## Discord Bot Setup
1. Go to https://discord.com/developers/applications and create a new application.
2. Under **Bot**, enable **Message Content Intent**, **Server Members Intent**, and **Guilds Intent**.
3. Copy the bot token. This is your `DISCORD_TOKEN`.
4. Under **OAuth2 → URL Generator**, select `bot` and `applications.commands`, and grant `Send Messages`, `Read Message History`, `Embed Links`, `Use Slash Commands`, and `Add Reactions`.
5. Use the generated URL to invite the bot to your server.

## Installation
```bash
git clone https://github.com/mojomast/rpg-dm-bot.git
cd rpg-dm-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuration
Set the following in `.env`:
- `DISCORD_TOKEN`
- `OPENROUTER_API_KEY` or `REQUESTY_API_KEY`
- `LLM_MODEL`
- `LLM_BASE_URL`
- `DATABASE_PATH`
- `DISCORD_GUILD_ID` if you want guild-scoped command sync during development

Optional OpenRouter headers:
- `OPENROUTER_SITE_URL`
- `OPENROUTER_APP_NAME`

## Running the Bot
```bash
python run.py
```

## Running the Web Dashboard
```bash
cd web
uvicorn api:app --reload --port 8000
```

## Updating Slash Commands
- If `DISCORD_GUILD_ID` is set, commands sync to that guild on startup.
- Otherwise, commands sync globally.

## Frontend Build
```bash
cd web/frontend
npm install
npm run build
```

## Troubleshooting
- If the bot does not start, check that `DISCORD_TOKEN` and one LLM API key are present in `.env`.
- If slash commands do not appear, confirm the bot was invited with the `applications.commands` scope.
- If the web dashboard cannot start, verify the backend dependencies and that the SQLite database path exists or can be created.
