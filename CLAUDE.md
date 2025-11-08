# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Discord bot built with discord.py 2.5.2, based on the Python Discord Bot Template by Krypton. The bot uses a cog-based architecture for organizing commands and features.

**Bot Name:** Lumbergh
**Python Version:** 3.12.9
**Architecture:** Cog-based command system with hybrid commands (slash + prefix)

## Development Commands

### Setup & Installation
```bash
# Install dependencies
python -m pip install -r requirements.txt

# Setup environment variables
# Copy .env.example to .env (note: .env.example was deleted, but .env exists)
# Required variables: TOKEN, PREFIX, INVITE_LINK
```

### Running the Bot
```bash
# Standard execution
python bot.py

# Docker execution
docker compose up -d --build
```

## Architecture

### Core Structure

**bot.py** - Main entry point containing:
- `DiscordBot` class (extends `commands.Bot`)
- Custom logging with colored console output and file logging (`discord.log`)
- Database initialization and management
- Global event handlers (`on_message`, `on_command_completion`, `on_command_error`)
- Status rotation task that changes bot presence every minute

**database/** - SQLite database management:
- `DatabaseManager` class handles all database operations
- `schema.sql` defines the `warns` table structure
- Async database operations using `aiosqlite`
- Database file: `database/database.db`

**cogs/** - Feature modules (commands are auto-loaded on startup):
- `general.py` - Bot info, server info, help, ping, 8ball, bitcoin price, feedback modal
- `moderation.py` - Kick, ban, nick, hackban, purge, archive, warning system (add/remove/list)
- `fun.py` - Fun/entertainment commands
- `owner.py` - Owner-only commands
- `reminders.py` - Comprehensive reminder system (one-time, recurring, scheduled)
- `template.py` - Template for creating new cogs

### Key Design Patterns

**Hybrid Commands:** All commands use `@commands.hybrid_command` to work as both slash commands and prefix commands.

**Bot Context Variables:**
- `self.bot.logger` - Access the logger from any cog
- `self.bot.database` - Access DatabaseManager instance
- `self.bot.bot_prefix` - Bot prefix from environment
- `self.bot.invite_link` - Bot invite link from environment

**Intents:** Uses `discord.Intents.default()`. Message content intent is disabled by default (line 67 in bot.py) but can be enabled for prefix commands.

**Database Pattern:** All database operations are async and use the centralized `DatabaseManager` class. Warnings are stored per-server with composite keys (user_id, server_id).

## Reminder System (reminders.py)

The reminders cog is the most complex feature with three types of reminders:

1. **One-time reminders:** `/remind <time> <message>` - Single notification after a delay
2. **Recurring reminders:** `/recurring <time> <message>` - Repeats at specified intervals
3. **Scheduled reminders:** `/schedule <pattern> <time> <message>` - Triggers at specific times/days

**Time Parsing:**
- Intervals: `5s`, `10m`, `2h`, `3d`, `1w` (handled by `parse_time()`)
- Time of day: `9:00 AM`, `2:30pm`, `14:30` (handled by `parse_time_of_day()`)
- Schedule patterns: `daily`, `weekdays`, `weekends`, `monday`, `monthly` (handled by `parse_schedule_pattern()`)

**Implementation Details:**
- Uses `asyncio.create_task()` for background workers
- `active_reminders` list tracks all tasks with metadata
- User limits: 5 total reminders, 3 recurring max
- Recurring reminders reschedule themselves automatically
- Scheduled reminders calculate next occurrence dynamically using `calculate_next_scheduled_time()`

## Creating New Commands

Use `cogs/template.py` as a starting point. Key requirements:

1. Inherit from `commands.Cog`
2. Use `@commands.hybrid_command` for commands
3. Include docstrings for all commands
4. Add `async def setup(bot)` function at the end
5. Use `@app_commands.describe()` for parameter descriptions
6. Access bot features via `self.bot.logger`, `self.bot.database`, etc.

Example:
```python
@commands.hybrid_command(
    name="mycommand",
    description="What the command does",
)
@app_commands.describe(param="Parameter description")
async def mycommand(self, context: Context, param: str) -> None:
    """Detailed docstring."""
    embed = discord.Embed(description="Response", color=0xBEBEFE)
    await context.send(embed=embed)
```

## Testing Slash Commands

Global slash commands take time to register. For instant testing, use guild-specific registration:

```python
@commands.hybrid_command(name="command", description="Command description")
@app_commands.guilds(discord.Object(id=GUILD_ID))  # Add your test guild ID
```

## Error Handling

The bot has centralized error handling in `bot.py` (`on_command_error`) for:
- `CommandOnCooldown` - Shows formatted retry time
- `NotOwner` - Logs attempted owner command usage
- `MissingPermissions` - Shows which permissions are missing
- `BotMissingPermissions` - Notifies about bot's missing permissions
- `MissingRequiredArgument` - Shows the missing argument

Add command-specific error handlers using `@command.error` decorator.

## Database Operations

When adding database functionality:

1. Add SQL schema to `database/schema.sql`
2. Add methods to `DatabaseManager` class in `database/__init__.py`
3. Use `await self.bot.database.your_method()` in cogs
4. All operations must be async
5. Always commit changes: `await self.connection.commit()`

## Embeds

Use consistent embed colors:
- Success: `0x2ecc71` (green) or `0xBEBEFE` (light purple)
- Error: `0xE02B2B` (red) or `0xe74c3c` (red variant)
- Info: `0x3498db` (blue)
- Special: `0x9b59b6` (purple for scheduled items), `0xD75BF4` (invite/server)

## Environment Variables

Required in `.env`:
- `TOKEN` - Discord bot token
- `PREFIX` - Command prefix for prefix commands (when enabled)
- `INVITE_LINK` - Bot invite URL

## Logging

Logs are written to both console (with colors) and `discord.log` file. Use `self.bot.logger` for logging within cogs:

```python
self.bot.logger.info("Info message")
self.bot.logger.warning("Warning message")
self.bot.logger.error("Error message")
```

## License & Attribution

This project is based on Krypton's template. When modifying:
- Keep copyright notices in file headers
- Maintain link to original template: https://github.com/kkrypt0nn
- Use Apache License 2.0 for unchanged template code
