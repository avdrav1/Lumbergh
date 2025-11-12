# Creative.py Command Consolidation Guide

## Current State: 18 Commands
1. `story-prompt` - Generate story writing prompts
2. `writing-prompt` - Generate general writing prompts
3. `story-start` - Start collaborative story
4. `song-prompt` - Generate song ideas
5. `chords` - Get chord progressions
6. `lyrics` - Generate song lyrics
7. `music-theory` - Music theory tips
8. `draw-prompt` - Art/drawing prompts
9. `style-challenge` - Art style challenges
10. `palette` - Color palette generator
11. `character-gen` - Character generator
12. `showcase` - Share creative work
13. `gallery` - View showcased work
14. `challenge-submit` - Submit to challenge
15. `challenge-view` - View challenges
16. `creative-schedule` - Setup daily prompts (admin)
17. `creative-theme` - Set monthly theme (admin)
18. `creative-config` - View configuration

## Target State: 6 Commands (-12 slots!)

###  1. `/creative-prompt [type]` [genre/style] [theme]`
**Consolidates:** story-prompt, writing-prompt, song-prompt, draw-prompt, character-gen, chords, lyrics, music-theory, style-challenge, palette

**Type Choices:**
- 📝 Writing - General writing prompts
- 📖 Story - Story-specific prompts with genre
- 🎵 Song - Song ideas and concepts
- 🎹 Chords - Chord progressions
- 🎤 Lyrics - Song lyrics
- 🎼 Theory - Music theory tips
- 🎨 Art - Drawing/art prompts
- 🖌️ Style - Art style challenges
- 🎨 Palette - Color palettes
- 👤 Character - Character generation

**Parameters:**
- `type` (required) - What type of prompt
- `genre_or_style` (optional) - Genre for story/music, style for art
- `theme` (optional) - Monthly theme or custom theme

**Implementation Pattern:**
```python
@commands.hybrid_command(name="creative-prompt")
@app_commands.describe(
    type="Type of creative prompt",
    genre_or_style="Genre (story/music) or style (art)",
    theme="Optional theme"
)
@app_commands.choices(type=[
    app_commands.Choice(name="📝 Writing", value="writing"),
    app_commands.Choice(name="📖 Story", value="story"),
    app_commands.Choice(name="🎵 Song", value="song"),
    app_commands.Choice(name="🎹 Chords", value="chords"),
    app_commands.Choice(name="🎤 Lyrics", value="lyrics"),
    app_commands.Choice(name="🎼 Music Theory", value="theory"),
    app_commands.Choice(name="🎨 Art", value="art"),
    app_commands.Choice(name="🖌️ Art Style", value="style"),
    app_commands.Choice(name="🎨 Palette", value="palette"),
    app_commands.Choice(name="👤 Character", value="character"),
])
async def creative_prompt(
    self,
    ctx: Context,
    type: str,
    genre_or_style: Optional[str] = None,
    theme: Optional[str] = None
) -> None:
    """Generate creative prompts of various types."""
    if ctx.interaction:
        await ctx.defer()

    # Route to appropriate generator based on type
    if type == "writing":
        result = await self.generate_writing_prompt(theme)
        emoji = "📝"
        title = "Writing Prompt"
    elif type == "story":
        result = await self.generate_story_prompt(genre_or_style or "random", theme)
        emoji = "📖"
        title = f"Story Prompt ({genre_or_style or 'Random'})"
    elif type == "song":
        result = await self.generate_song_prompt(genre_or_style)
        emoji = "🎵"
        title = "Song Idea"
    # ... etc for all types

    embed = discord.Embed(
        title=f"{emoji} {title}",
        description=result,
        color=0x9B59B6
    )
    await ctx.send(embed=embed)
```

### 2. `/creative-collab`
**Consolidates:** story-start (KEEP AS-IS, just rename)

**No changes needed** - This command starts collaborative stories and is unique enough to keep separate.

### 3. `/creative-gallery [action]`
**Consolidates:** showcase, gallery

**Action Choices:**
- `submit` - Share your creative work
- `view` - Browse showcased work
- `my-work` - View your submissions

**Implementation:**
```python
gallery_group = app_commands.Group(
    name="creative-gallery",
    description="Share and view creative work"
)

@gallery_group.command(name="submit")
@app_commands.describe(
    work_type="Type of work",
    title="Title of your work",
    content="Description or text content",
    image_url="Optional image URL"
)
async def submit(self, interaction, work_type: str, title: str, content: str, image_url: str = None):
    # showcase logic
    pass

@gallery_group.command(name="view")
@app_commands.describe(filter="Filter by work type")
async def view(self, interaction, filter: str = "all"):
    # gallery logic
    pass

@gallery_group.command(name="my-work")
async def my_work(self, interaction):
    # Show user's submissions
    pass
```

### 4. `/creative-challenge [action]`
**Consolidates:** challenge-submit, challenge-view

**Action Choices:**
- `view` - View current challenges
- `submit` - Submit to a challenge
- `vote` - Vote on submissions (if applicable)

### 5. `/creative-admin [action]`
**Consolidates:** creative-schedule, creative-theme, creative-config

**Action Choices:**
- `schedule` - Setup daily prompt posts
- `theme` - Set monthly theme
- `config` - View current configuration
- `toggle` - Enable/disable features

**Requires:** Administrator permissions

### 6. `/creative-help`
**New command** - Provides guidance on using creative features

---

## Step-by-Step Refactoring Plan

### Phase 1: Backup & Preparation
1. ✅ Create backup: `cp cogs/creative.py cogs/creative.py.backup`
2. ✅ Document all current commands
3. ✅ Identify shared helper methods

### Phase 2: Create New Command Structure
1. Keep all helper methods unchanged:
   - `generate_story_prompt()`
   - `generate_writing_prompt()`
   - `generate_song_prompt()`
   - `generate_chord_progression()`
   - `generate_lyrics()`
   - `generate_music_theory_tip()`
   - `generate_draw_prompt()`
   - `generate_color_palette()`
   - `generate_character()`

2. Create new main command `/creative-prompt`:
   - Add type parameter with choices
   - Route to appropriate helper method
   - Maintain all existing functionality

3. Rename `/story-start` → `/creative-collab`

4. Create command groups:
   - `creative-gallery` group
   - `creative-challenge` group
   - `creative-admin` group

### Phase 3: Migrate Logic
For each old command, move the logic into the new structure:

**Example: story-prompt migration**
```python
# OLD (lines ~526-570)
@commands.hybrid_command(name="story-prompt")
async def story_prompt(self, ctx, genre: str = "random", theme: Optional[str] = None):
    # ... implementation ...
    pass

# NEW (inside creative_prompt)
if type == "story":
    result = await self.generate_story_prompt(genre_or_style or "random", theme)
    # ... format and send ...
```

### Phase 4: Handle Command Groups
Use `app_commands.Group` instead of multiple `hybrid_command` decorators:

```python
# In __init__
self.gallery_group = app_commands.Group(
    name="creative-gallery",
    description="Share and view creative work"
)
self.bot.tree.add_command(self.gallery_group)

self.challenge_group = app_commands.Group(
    name="creative-challenge",
    description="Participate in creative challenges"
)
self.bot.tree.add_command(self.challenge_group)

self.admin_group = app_commands.Group(
    name="creative-admin",
    description="Admin commands for creative features",
    default_permissions=discord.Permissions(administrator=True)
)
self.bot.tree.add_command(self.admin_group)
```

### Phase 5: Testing Checklist
- [ ] `/creative-prompt` works with all 10 types
- [ ] `/creative-collab` starts collaborative stories
- [ ] `/creative-gallery submit` works
- [ ] `/creative-gallery view` displays work
- [ ] `/creative-challenge view` shows challenges
- [ ] `/creative-challenge submit` accepts submissions
- [ ] `/creative-admin schedule` configures daily posts
- [ ] `/creative-admin theme` sets monthly theme
- [ ] `/creative-admin config` shows settings
- [ ] Background tasks still function
- [ ] Database operations intact
- [ ] All error handling works

---

## Migration Notes

### User Impact
Users will need to learn new command structure:
- Old: `/story-prompt fantasy`
- New: `/creative-prompt story fantasy`

- Old: `/showcase writing "My Story" "content"`
- New: `/creative-gallery submit writing "My Story" "content"`

### Announcement Template
```
📢 Creative Commands Update!

We've reorganized creative commands to streamline your experience:

**Prompts (all in one!):**
• `/creative-prompt [type]` - Get writing, story, music, art prompts
  - Types: writing, story, song, chords, lyrics, theory, art, style, palette, character

**Gallery:**
• `/creative-gallery submit` - Share your work
• `/creative-gallery view` - Browse creations

**Challenges:**
• `/creative-challenge view` - See current challenges
• `/creative-challenge submit` - Submit your entry

**Admin:**
• `/creative-admin schedule` - Daily prompt setup
• `/creative-admin theme` - Monthly themes

Old commands still work for now but will be removed soon. Please update!
```

---

## Files to Modify
1. `cogs/creative.py` - Main refactor
2. `CREATIVE_STUDIO_GUIDE.md` - Update documentation
3. Bot changelog/announcements - Notify users

---

## Estimated Time
- **Planning:** 30 min (done!)
- **Implementation:** 3-4 hours
- **Testing:** 1-2 hours
- **Documentation:** 30 min
- **Total:** 5-7 hours

---

## Alternative: Minimal Approach

If 5-7 hours is too much, we can do a **super minimal** approach:

### Keep Only Top Commands (18 → 8 commands = -10 slots)

**Keep as-is:**
1. `/story-prompt` - Most used
2. `/writing-prompt` - Most used
3. `/song-prompt` - Most used
4. `/draw-prompt` - Most used
5. `/character-gen` - Most used
6. `/showcase` - Core feature
7. `/gallery` - Core feature

**Remove/Consolidate:**
- `chords` + `lyrics` + `music-theory` → `/song-prompt` (add parameter)
- `style-challenge` + `palette` → `/draw-prompt` (add parameter)
- `challenge-submit` + `challenge-view` → `/showcase` (add parameter)
- `creative-schedule` + `creative-theme` + `creative-config` + `story-start` → Remove or make admin-only slash commands

This saves 10 slots with minimal code changes!
