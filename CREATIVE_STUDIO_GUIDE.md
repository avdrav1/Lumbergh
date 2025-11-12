# Creative Studio Guide

## Overview
A comprehensive creative collaboration system with AI-powered prompts for writing, music, and art. Features include collaborative projects, weekly challenges, a community gallery, and scheduled daily prompts.

## Commands by Category

### ✍️ Writing Commands

#### `/story-prompt [genre] [theme]`
Generate a story writing prompt.
- **Genres:** fantasy, scifi, mystery, romance, horror, thriller, adventure, historical, random
- **Theme:** Optional theme to incorporate (uses monthly theme if not specified)

Example: `/story-prompt fantasy dragons`

#### `/writing-prompt [style]`
Get a writing exercise or technique prompt.
- **Styles:** general, description, dialogue, pacing, character, worldbuilding
- **Duration:** 15-30 minute exercises

Example: `/writing-prompt character`

#### `/story-start <prompt>`
Start a collaborative story in a dedicated thread.
- Creates a new thread for collaborative storytelling
- Multiple users can contribute
- Mention @Bot to have AI continue the story
- Each contribution: 100-500 words

Example: `/story-start A wizard discovers their magic is fading`

---

### 🎵 Music Commands

#### `/song-prompt [genre] [theme]`
Generate a songwriting prompt with title, theme, and opening line.
- **Genres:** pop, rock, jazz, blues, country, hiphop, electronic, classical, folk, random

Example: `/song-prompt rock heartbreak`

#### `/chords [genre] [mood]`
Generate a chord progression.
- **Genres:** pop, rock, jazz, blues, country, hiphop, electronic, classical, folk, random
- **Moods:** happy, sad, energetic, calm, mysterious, romantic, dark, uplifting
- Returns: Chord progression, key, and description

Example: `/chords pop happy`

#### `/lyrics [genre] [theme]`
Generate lyric ideas (a verse).
- **Themes:** Any subject (love, loss, hope, freedom, etc.)
- Returns: 4-8 lines of lyrics

Example: `/lyrics folk nature`

#### `/music-theory <topic>`
Get help with music theory concepts.
- **Topics:** scales, chords, harmony, rhythm, keys, progressions, etc.
- Beginner to intermediate level explanations

Example: `/music-theory circle of fifths`

---

### 🎨 Art Commands

#### `/draw-prompt [style] [theme]`
Generate a drawing/art prompt.
- **Styles:** realistic, anime, cartoon, abstract, impressionist, surreal, minimalist, steampunk, cyberpunk, random

Example: `/draw-prompt anime cyberpunk`

#### `/style-challenge`
Get an art style challenge with constraints.
- Returns: Style/medium, subject, and creative constraint
- Pushes you outside your comfort zone

Example: `/style-challenge`

#### `/palette [theme]`
Generate a color palette with hex codes.
- **Themes:** nature, sunset, ocean, forest, autumn, winter, neon, pastel, monochrome, vibrant, random
- Returns: 5 coordinated colors with hex codes

Example: `/palette sunset`

#### `/character-gen [archetype]`
Generate a detailed character description for drawing.
- **Archetypes:** hero, villain, mentor, trickster, rebel, innocent, explorer, sage, random
- Returns: Appearance, personality, unique traits

Example: `/character-gen villain`

---

### 🤝 Collaboration Commands

#### `/story-start <prompt>`
Start a collaborative project (see Writing Commands above)
- Creates dedicated thread
- AI participation via @Bot mention
- Community storytelling

#### AI Participation
- In any collaborative thread, mention @Bot
- AI will continue the story naturally
- Tracks contributions automatically

---

### 🏆 Challenge Commands

#### `/challenge-submit <challenge_id> <submission> [url]`
Submit your work to a weekly challenge.
- **challenge_id:** Get from weekly challenge post
- **submission:** Your work description or actual text
- **url:** Optional link to image, audio, etc.
- Can update submission before deadline

Example: `/challenge-submit 5 "A story about a time traveler who..." https://imgur.com/...`

#### `/challenge-view <challenge_id>`
View all submissions for a challenge.
- Shows all entries
- Displays vote counts
- Lists top submissions

Example: `/challenge-view 5`

---

### 🖼️ Gallery Commands

#### `/showcase <work_type> <title> <description> [image_url]`
Share your completed creative work in the gallery.
- **work_type:** story, music, art
- **title:** Name of your work
- **description:** What it's about
- **image_url:** Optional image link

Example: `/showcase art "Sunset Dreams" "Watercolor painting of a mountain sunset" https://...`

#### `/gallery [work_type]`
Browse the creative gallery.
- **Filter:** Optional - story, music, or art
- Shows recent 10 works
- Displays reactions/appreciation

Example: `/gallery art`

---

### ⚙️ Admin Commands (Require Administrator)

#### `/creative-schedule <channel> <time> <timezone>`
Schedule daily creative prompts.
- **channel:** Text channel to post in
- **time:** HH:MM format (24-hour)
- **timezone:** UTC offset (-12 to +14)
- **Rotation:** Writing → Music → Art (cycles daily)

Example: `/creative-schedule #creative 14:00 -5`

#### `/creative-theme <theme>`
Set the monthly creative theme.
- Influences all prompts for the month
- Optional but recommended
- Builds community cohesion around themes

Example: `/creative-theme Space Exploration`

#### `/creative-config`
View current configuration.
- Shows channel, post time, timezone
- Displays daily/weekly status
- Shows current monthly theme

---

## Features in Detail

### 📅 Scheduled Daily Prompts
- Automatically posts at configured time
- Rotates between writing, music, and art
- Incorporates monthly theme if set
- Checks every 15 minutes

**Example Schedule:**
- Monday: Writing prompt
- Tuesday: Music prompt
- Wednesday: Art prompt
- Thursday: Writing prompt
- (continues rotating)

### 🏅 Weekly Challenges
- Posts every Monday (automatically)
- Random type: writing, music, or art
- 7-day submission window
- Community voting after deadline
- Showcases creativity

**Challenge Flow:**
1. Challenge posted Monday morning
2. Submit throughout the week
3. View submissions anytime
4. Voting enabled after deadline
5. Winner announced

### 🎨 Monthly Themes
- Admins set theme each month
- All prompts incorporate theme
- Optional but enhances cohesion
- Examples: "Ocean Life", "Time Travel", "Dreams"

### 🤖 AI Participation
- Mention the bot in collaborative threads
- AI continues stories naturally
- Matches established tone/style
- Tracks contributions automatically
- Treats AI as another collaborator

### 🖼️ Community Gallery
- Permanent showcase for completed works
- React to show appreciation
- Filter by work type
- Browse community creativity
- Encourages sharing

---

## Database Tables

### `creative_config`
Server configuration for scheduled prompts and themes.

### `collaborative_works`
Tracks active and completed collaborative projects.

### `work_contributions`
Individual contributions to collaborative works.

### `creative_challenges`
Weekly creative challenges with prompts and deadlines.

### `challenge_submissions`
User submissions to challenges with vote counts.

### `creative_gallery`
Showcased creative works from the community.

---

## Usage Examples

### For Writers
```
/story-prompt mystery             # Get a mystery prompt
/writing-prompt dialogue          # Practice dialogue
/story-start A detective finds... # Start collaborative story
# In thread: @Bot                 # Have AI continue
/showcase story "Title" "Desc"    # Share finished work
```

### For Musicians
```
/song-prompt rock               # Get song idea
/chords rock energetic          # Get chord progression
/lyrics rock adventure          # Get lyric ideas
/music-theory modes             # Learn theory
/showcase music "Song" "About..."
```

### For Artists
```
/draw-prompt anime              # Get drawing prompt
/style-challenge                # Get challenge
/palette sunset                 # Get color palette
/character-gen hero             # Get character
/showcase art "Title" "Desc" URL
```

### For Server Admins
```
/creative-schedule #creative 18:00 -8    # West Coast time
/creative-theme Autumn Vibes              # Set monthly theme
/creative-config                          # Check settings
```

---

## Tips & Best Practices

### For Community Engagement
1. **Set Monthly Themes:** Creates cohesion and gives direction
2. **Promote Daily Prompts:** Encourage members to participate
3. **Highlight Gallery Works:** React and comment on submissions
4. **Run Challenges Consistently:** Weekly challenges build anticipation
5. **Use Dedicated Channel:** Keep creative content organized

### For Creators
1. **Save Prompts:** Screenshot or note prompts that inspire you
2. **Participate Regularly:** Daily prompts are quick inspiration
3. **Collaborate:** Jump into collaborative threads
4. **Share Your Work:** Use /showcase to build your portfolio
5. **Support Others:** React to gallery submissions

### For Collaborative Stories
1. **Read Previous Contributions:** Maintain continuity
2. **Match the Tone:** Keep consistent voice
3. **Add 100-500 Words:** Not too short, not too long
4. **Mention @Bot:** Have AI contribute when stuck
5. **Build on Ideas:** Develop what others started

---

## Troubleshooting

### Prompts Not Generating
- Verify ANTHROPIC_API_KEY is set in .env
- Check logs for API errors
- Bot will show error message if Claude unavailable

### Scheduled Prompts Not Posting
- Verify configuration with `/creative-config`
- Check channel still exists
- Ensure bot has post permissions
- Background task checks every 15 minutes

### AI Not Participating in Threads
- Must mention @Bot in the thread
- Thread must be a collaborative work thread (created with /story-start)
- Check bot has thread permissions

### Challenge Submissions Failing
- Verify challenge hasn't ended
- Check challenge ID is correct
- Use `/challenge-view <id>` to confirm challenge exists

---

## Implementation Details

### Files Created/Modified
- `cogs/creative.py` - Main creative cog (~1,450 lines)
- `database/schema.sql` - Added 6 creative tables
- `database/migrate_add_creative.py` - Migration script

### AI Integration
- **Model:** claude-3-5-haiku-20241022
- **Generates:** Prompts, continuations, explanations
- **Max Tokens:** 150-400 depending on task
- **Fallbacks:** Hardcoded defaults if API unavailable

### Background Tasks
- **Daily Prompts:** Check every 15 minutes, 60-minute posting window
- **Weekly Challenges:** Check hourly, posts Mondays
- **Rotation:** Writing → Music → Art → Writing...

### Patterns Used
- Same Claude model as other cogs
- Consistent embed styling (category-specific colors)
- Admin-only configuration commands
- Hybrid commands (slash + prefix support)
- Graceful degradation with fallbacks
- Automatic thread creation for collaboration

---

## Future Enhancement Ideas

- User voting on challenge submissions
- Collaborative playlist building
- Art critique/feedback system
- Progress tracking for participants
- Badges/achievements for milestones
- Export collaborative works
- Archive system for old challenges
- Cross-server creative exchanges
- Multi-language support
- Image generation integration

---

## Color Scheme

**Writing:** 🟣 Purple (#9B59B6, #3498DB)
**Music:** 🔴 Pink/Red (#E91E63, #FF5722, #9C27B0)
**Art:** 🟠 Orange/Brown (#FF9800, #795548)
**Gallery:** 🟡 Gold (#FFD700)
**Challenges:** 🔴 Red (#FF6B6B)
**Success:** 🟢 Green (#2ECC71)
**Error:** 🔴 Red (#E02B2B)

---

## Support

For issues or feature requests, check bot logs in `discord.log` or review the implementation in `cogs/creative.py`.

Enjoy creating! ✨
