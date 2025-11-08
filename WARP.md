# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Commands

- Setup (Python 3.12):
  - python -m venv .venv && source .venv/bin/activate
  - python -m pip install -r requirements.txt
  - Create a .env with: TOKEN={{DISCORD_BOT_TOKEN}}, PREFIX={{COMMAND_PREFIX}}, INVITE_LINK={{BOT_INVITE_URL}}
- Run locally:
  - python bot.py
- Docker:
  - docker compose up -d --build
  - Image build only: docker build -t python-discord-bot-template .
- Slash command sync (owner-only, run inside Discord using your prefix):
  - {PREFIX}sync global  (register everywhere; takes time)
  - {PREFIX}sync guild   (instant for current guild)
  - To clear: {PREFIX}unsync global | {PREFIX}unsync guild
- Cog management (hot-reload without restarting the bot):
  - {PREFIX}reload reminders | {PREFIX}load <cog> | {PREFIX}unload <cog>
- Logging/DB locations:
  - Logs: discord.log (also mounted in Docker)
  - SQLite DB: database/database.db
- Tests/lint:
  - No test suite is configured in this repo.
  - Optional formatting (Black style referenced in README): python -m pip install black && black .

## Architecture and structure

- Entry point (bot.py):
  - Subclasses discord.ext.commands.Bot as DiscordBot; loads env via python-dotenv.
  - Sets up dual logging (console with colorized formatter, file to discord.log).
  - Initializes SQLite via aiosqlite; executes database/schema.sql on startup; exposes DatabaseManager as bot.database.
  - Auto-loads all cogs in cogs/ on startup (async load_extension loop) and starts a periodic status task.
  - Handles on_message, on_command_completion, and on_command_error for global behavior and user feedback.
- Database (database/__init__.py, database/schema.sql):
  - Warns table for moderation; DatabaseManager exposes add_warn, remove_warn, get_warnings used by moderation commands.
- Cogs (cogs/*.py): organized by domain, primarily hybrid commands (slash + prefix) unless noted.
  - general.py: Help aggregator (inspects loaded cogs), bot/server info, ping, invite/server links, simple web-API usage (bitcoin), and context menu commands (grab ID, remove spoilers).
  - moderation.py: kick/ban/nick, purge, hackban, archive channel logs to a file, and a warning subcommand group (add/remove/list) backed by the DB.
  - owner.py (owner-only): slash sync/unsync helpers (global/guild), cog load/unload/reload, shutdown, utility say/embed.
  - reminders.py: in-memory reminder system supporting one-time, recurring (interval), and scheduled (daily/weekday/weekend/weekly/monthly) reminders. Implements parsers for time and schedule expressions, background workers via asyncio.create_task, listing and cancellation commands, and status/reporting.
  - fun.py: random fact (HTTP API), coinflip with buttons, rock-paper-scissors with UI selects.
  - template.py: scaffold cog showing hybrid command wiring.
- Intents:
  - Uses discord.Intents.default(); privileged intents (members, message_content, presences) are not enabled in code.
  - Some features (e.g., message content dependent actions like archiving channel text) may require enabling Message Content Intent in the Discord developer portal and, if needed, uncommenting intents.message_content in bot.py.
- Docker:
  - Dockerfile uses python:3.12-slim, installs requirements, runs python bot.py.
  - docker-compose.yaml mounts ./database and ./discord.log into the container for persistence.

## Notes for Warp

- Environment: load .env at runtime; never print or log TOKEN. Use env placeholders (e.g., {{DISCORD_BOT_TOKEN}}) when generating commands.
- When adding new cogs, place files under cogs/ and ensure they define async def setup(bot): await bot.add_cog(...). They are auto-loaded at startup; use owner reload to iterate quickly.
- If adding DB-backed features, extend DatabaseManager and schema.sql; init_db in bot.py will apply schema on startup.