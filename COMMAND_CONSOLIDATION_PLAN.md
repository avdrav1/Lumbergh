# Command Consolidation Plan

## Problem
Bot has **127 slash commands**, but Discord's global limit is **100 commands**.

## Solution
Consolidate related commands using `app_commands.Group` to reduce command count to **~69 commands** (31 under limit).

---

## Implementation Guide

### Pattern for Command Groups

```python
# Create a command group
admin_group = app_commands.Group(
    name="feature-admin",
    description="Admin commands for feature management"
)

# Add commands to the group
@admin_group.command(name="setup")
@app_commands.describe(channel="Channel to post in")
async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
    """Setup the feature."""
    # Implementation
    pass

# Register the group in __init__
self.bot.tree.add_command(admin_group)
```

**Usage in Discord:**
- Before: `/feature-setup`, `/feature-toggle`, `/feature-status`
- After: `/feature-admin setup`, `/feature-admin toggle`, `/feature-admin status`

---

## 1. Affirmations (5 → 2 commands) **-3 slots**

### Current Commands:
1. `/affirmation` - Get affirmation
2. `/affirmation-setup` - Configure daily posts
3. `/affirmation-toggle` - Enable/disable
4. `/affirmation-now` - Manual post
5. `/affirmation-status` - View config

### New Structure:
1. `/affirmation [theme]` - Get affirmation (KEEP AS-IS)
2. `/affirmation-admin [action]` - All admin functions

### Implementation:
```python
# Keep main command unchanged
@commands.hybrid_command(name="affirmation")
async def affirmation(self, ctx, theme: str = "motivation"):
    # Existing code
    pass

# Create admin group
admin_group = app_commands.Group(
    name="affirmation-admin",
    description="Admin commands for affirmations",
    default_permissions=discord.Permissions(administrator=True)
)

@admin_group.command(name="setup")
async def setup(self, interaction, channel, time, timezone, theme):
    # Move affirmation-setup logic here
    pass

@admin_group.command(name="toggle")
async def toggle(self, interaction, enabled: bool):
    # Move affirmation-toggle logic here
    pass

@admin_group.command(name="now")
async def now(self, interaction):
    # Move affirmation-now logic here
    pass

@admin_group.command(name="status")
async def status(self, interaction):
    # Move affirmation-status logic here
    pass
```

---

## 2. Recipe (6 → 3 commands) **-3 slots**

### Current Commands:
1. `/recipe` - Generate recipe
2. `/recipe-from` - From ingredients
3. `/recipe-book` - View saved
4. `/recipe-delete` - Delete recipe
5. `/recipe-daily-setup` - Configure daily
6. `/recipe-daily-disable` - Disable daily

### New Structure:
1. `/recipe [cuisine] [dietary] [difficulty]` - Generate (KEEP)
2. `/recipe-from <ingredients>` - From ingredients (KEEP)
3. `/recipe-book [action]` - View/manage saved recipes
4. `/recipe-admin [action]` - Daily post settings

### Implementation:
```python
# Keep main commands
@commands.hybrid_command(name="recipe")
async def recipe(self, ctx, cuisine, dietary, difficulty):
    pass

@commands.hybrid_command(name="recipe-from")
async def recipe_from(self, ctx, ingredients):
    pass

# Create book group
book_group = app_commands.Group(name="recipe-book", description="Manage saved recipes")

@book_group.command(name="view")
@app_commands.describe(page="Page number")
async def view(self, interaction, page: int = 1):
    # Current recipe-book logic
    pass

@book_group.command(name="delete")
@app_commands.describe(recipe_id="Recipe ID to delete")
async def delete(self, interaction, recipe_id: int):
    # Current recipe-delete logic
    pass

# Create admin group
admin_group = app_commands.Group(
    name="recipe-admin",
    description="Admin commands for recipes",
    default_permissions=discord.Permissions(administrator=True)
)

@admin_group.command(name="setup")
async def setup(self, interaction, channel, post_time, timezone_offset, cuisine, dietary):
    # recipe-daily-setup logic
    pass

@admin_group.command(name="disable")
async def disable(self, interaction):
    # recipe-daily-disable logic
    pass
```

---

## 3. Trivia (10 → 4 commands) **-6 slots**

### Current Commands:
1. `/trivia` - Play trivia
2. `/trivia-categories` - List categories
3. `/trivia-scores` - Leaderboard
4. `/trivia-stats` - Personal stats
5. `/trivia-schedule` - Setup daily
6. `/trivia-toggle` - Enable/disable
7. `/trivia-config` - View config
8. (Plus ~3 more)

### New Structure:
1. `/trivia [category] [difficulty]` - Play (KEEP)
2. `/trivia-stats [action]` - Scores, leaderboard, personal
3. `/trivia-admin [action]` - Schedule, toggle, config
4. `/trivia-help` - Categories and info

---

## 4. News (10 → 3 commands) **-7 slots**

### Current Commands:
1. `/news` - View news
2. `/news-setup` - Configure
3. `/news-toggle` - Enable/disable
4. `/news-status` - View config
5. `/news-sources` - List sources
6. `/news-now` - Manual post
7. `/news-remove` - Remove time
8. `/news-add-source` - Add source
9. `/news-remove-source` - Remove source
10. (Plus 1 more)

### New Structure:
1. `/news [action]` - View news, manual post
2. `/news-sources [action]` - Add, remove, list sources
3. `/news-admin [action]` - Setup, toggle, status, config

---

## 5. Vibes (14 → 4 commands) **-10 slots**

### Current Commands:
1. `/remember` - Save memory
2. `/memories` - View memories
3. `/memory-stats` - Statistics
4. `/qotd` - Question of the day
5. `/qotd-suggest` - Suggest question
6. `/vibes-setup` - Configure
7. `/vibes-toggle` - Enable features
8. `/vibes-status` - View config
9. (Plus ~6 more)

### New Structure:
1. `/vibes-memory [action]` - Remember, view, stats, delete
2. `/vibes-qotd [action]` - Get question, suggest, manual post
3. `/vibes-admin [action]` - Setup, toggle, status
4. `/vibes-help` - Guide to features

---

## 6. Creative (27 → 6 commands) **-21 slots** ⭐ BIGGEST SAVINGS

### Current Commands:
**Writing:** story-prompt, writing-prompt, story-start
**Music:** song-prompt, chords, lyrics, music-theory
**Art:** draw-prompt, style-challenge, palette, character-gen
**Gallery:** showcase, gallery, challenge-submit, challenge-view
**Admin:** creative-schedule, creative-theme, creative-config
(Plus ~9 more)

### New Structure:
1. `/creative-prompt [type]` - All prompt types (writing, music, art, character)
2. `/creative-collab` - Start collaborative stories
3. `/creative-showcase [action]` - Submit, view gallery
4. `/creative-challenge [action]` - Submit, view, vote
5. `/creative-admin [action]` - Schedule, theme, config
6. `/creative-help` - Guide to creative features

### Implementation:
```python
# Consolidated prompts
@commands.hybrid_command(name="creative-prompt")
@app_commands.describe(
    type="Type of prompt to generate"
)
@app_commands.choices(type=[
    app_commands.Choice(name="📝 Writing", value="writing"),
    app_commands.Choice(name="📖 Story", value="story"),
    app_commands.Choice(name="🎵 Song", value="song"),
    app_commands.Choice(name="🎨 Drawing", value="art"),
    app_commands.Choice(name="👤 Character", value="character"),
    app_commands.Choice(name="🎹 Chords", value="chords"),
    app_commands.Choice(name="🎤 Lyrics", value="lyrics"),
    app_commands.Choice(name="🎼 Music Theory", value="theory"),
])
async def creative_prompt(self, ctx, type: str):
    """Generate creative prompts of various types."""
    if type == "writing":
        # Old writing-prompt logic
        pass
    elif type == "story":
        # Old story-prompt logic
        pass
    elif type == "song":
        # Old song-prompt logic
        pass
    # ... etc
```

---

## 7. Reminders (12 → 4 commands) **-8 slots**

### Current Commands:
1. `/remind` - One-time reminder
2. `/recurring` - Recurring reminder
3. `/schedule` - Scheduled reminder
4. `/reminders` - List reminders
5. `/stoprecurring` - Stop recurring
6. `/stopscheduled` - Stop scheduled
7. `/stopreminder` - Stop reminder
8. `/testremin` - Test reminder
9. `/testschedule` - Test schedule
10. `/reminstat` - Statistics
11. `/reminderhelp` - Help
12. (Error handler)

### New Structure:
1. `/remind [time] [message]` - One-time (KEEP)
2. `/remind-recurring [interval] [message]` - Recurring
3. `/remind-scheduled [pattern] [time] [message]` - Scheduled
4. `/remind-manage [action]` - List, stop, stats, test, help

---

## Total Impact

| Cog | Before | After | Saved |
|-----|--------|-------|-------|
| creative.py | 27 | 6 | **-21** |
| vibes.py | 14 | 4 | **-10** |
| reminders.py | 12 | 4 | **-8** |
| news.py | 10 | 3 | **-7** |
| trivia.py | 10 | 4 | **-6** |
| affirmations.py | 5 | 2 | **-3** |
| recipe.py | 6 | 3 | **-3** |
| **OTHER COGS** | 43 | 43 | 0 |
| **TOTAL** | **127** | **69** | **-58** |

**Final: 69 commands (31 under limit!)**

---

## Testing Checklist

After consolidation, test:

- [ ] All commands register successfully
- [ ] Slash command autocomplete shows groups
- [ ] Group commands work in Discord
- [ ] Permissions still apply correctly
- [ ] Cooldowns still work
- [ ] Error handling intact
- [ ] Database calls unchanged
- [ ] Background tasks still function
- [ ] Existing functionality preserved

---

## Migration Notes

1. **User Impact:** Command names change, but functionality identical
2. **Announcement:** Notify users of new command structure
3. **Documentation:** Update all guides with new commands
4. **Gradual Rollout:** Consider keeping old commands temporarily with deprecation warnings
5. **Sync Commands:** Run `/sync` after deployment to register new structure

---

## Next Steps

1. Review this plan
2. Decide on implementation priority
3. Start with smallest cog (affirmations) to establish pattern
4. Test thoroughly in development server
5. Roll out to production
6. Update all documentation
7. Announce changes to users
