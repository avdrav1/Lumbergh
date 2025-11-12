# Trivia System Guide

## Overview
A comprehensive interactive trivia system with AI-generated questions, scoring, leaderboards, and scheduled daily games.

## Commands

### Player Commands

#### `/trivia [category] [difficulty]`
Start a single trivia question with interactive buttons.
- **Categories:** general, science, history, geography, entertainment, sports, technology, random
- **Difficulty:** easy (10 pts), medium (20 pts), hard (30 pts)
- **Cooldown:** 3 seconds per user
- **Timeout:** 30 seconds to answer

Example: `/trivia science hard`

#### `/trivia-categories`
List all available trivia categories with descriptions.

#### `/trivia-scores`
View the server leaderboard showing top 10 players by:
- Total points
- Accuracy percentage
- Best streak

#### `/trivia-stats [user]`
View detailed statistics for yourself or another user:
- Total points and questions answered
- Accuracy percentage
- Current and best streak
- Favorite category

### Admin Commands (Require Administrator Permission)

#### `/trivia-schedule <channel> <time> <timezone>`
Schedule daily trivia games.
- **channel:** Text channel to post in
- **time:** HH:MM format (24-hour), e.g., "14:00"
- **timezone:** UTC offset (-12 to +14), e.g., -5 for EST

Example: `/trivia-schedule #general 14:00 -5`

#### `/trivia-toggle <enabled>`
Enable or disable scheduled trivia posting.

Example: `/trivia-toggle true`

#### `/trivia-config`
View current trivia configuration including:
- Channel
- Post time and timezone
- Enabled status
- Questions per game
- Default difficulty

## Scoring System

### Base Points
- **Easy:** 10 points
- **Medium:** 20 points
- **Hard:** 30 points

### Streak Bonus
- +5 points per consecutive correct answer
- Maximum bonus: +50 points
- Resets on incorrect answer

### Example
- Answer 5 hard questions correctly in a row:
  - Q1: 30 pts (base)
  - Q2: 30 + 5 = 35 pts (1 streak bonus)
  - Q3: 30 + 10 = 40 pts (2 streak bonus)
  - Q4: 30 + 15 = 45 pts (3 streak bonus)
  - Q5: 30 + 20 = 50 pts (4 streak bonus)
  - Total: 200 points

## Features

### Interactive Buttons
- Questions display with A, B, C, D button options
- 30-second timer per question
- Instant feedback on answers
- Shows explanation after timeout

### AI-Generated Questions
- Powered by Claude 3.5 Haiku
- Fresh questions every time
- Context-appropriate difficulty
- Fallback questions if API unavailable

### Scheduled Daily Games
- Automatic posting at configured time
- Timezone-aware scheduling
- Checks every 15 minutes
- 60-minute posting window

### Statistics Tracking
- Per-server leaderboards
- Individual player stats
- Question history
- Category preferences

## Database Tables

### `trivia_config`
Stores server configuration for scheduled games.

### `trivia_scores`
Tracks player statistics per server:
- Total correct/answered
- Current and best streak
- Total points
- Last played timestamp

### `trivia_history`
Records every question answered:
- Question and answers
- Category and difficulty
- Points earned
- Timestamp

## Categories

- 🧠 **General** - General knowledge covering various topics
- 🔬 **Science** - Physics, chemistry, biology, astronomy
- 📜 **History** - Historical events, figures, and periods
- 🌍 **Geography** - Countries, capitals, landmarks
- 🎬 **Entertainment** - Movies, TV, music, pop culture
- ⚽ **Sports** - Sports, athletes, sporting events
- 💻 **Technology** - Computers, innovations, tech history
- 🎲 **Random** - Any topic

## Tips for Server Admins

1. **Choose Active Times:** Schedule trivia during peak server activity
2. **Promote Competition:** Announce leaderboard updates to encourage participation
3. **Mix Difficulties:** Use `/trivia` with different difficulties to engage all skill levels
4. **Timezone:** Make sure to use your server's primary timezone for scheduling

## Implementation Details

### Files Created/Modified
- `cogs/trivia.py` - Main trivia cog (~850 lines)
- `database/schema.sql` - Added 3 trivia tables
- `database/migrate_add_trivia.py` - Migration script

### Patterns Used
- Same Claude model as other cogs (claude-3-5-haiku-20241022)
- 15-minute scheduling loop like affirmations/news
- Consistent embed colors and styling
- Admin-only configuration commands
- Hybrid commands (slash + prefix support)
- Graceful degradation with fallback questions

### Dependencies
- discord.py 2.5.2
- anthropic (AsyncAnthropic)
- aiosqlite (via DatabaseManager)

## Troubleshooting

### Buttons Not Working
- Ensure bot has "Use Application Commands" permission
- Check bot has "Send Messages" and "Embed Links" permissions

### Scheduled Trivia Not Posting
- Verify configuration with `/trivia-config`
- Check channel still exists and bot has permissions
- Ensure trivia is enabled with `/trivia-toggle true`
- Background task checks every 15 minutes

### AI Questions Not Generating
- Verify ANTHROPIC_API_KEY is set in .env
- Bot will use fallback questions automatically
- Check logs for API errors

## Future Enhancements (Optional)

- Multi-question game mode `/trivia-game <questions>`
- Category-specific leaderboards
- Timed tournaments
- Team-based trivia
- Question suggestions from users
- Difficulty adjustment based on player skill
- Image-based questions
- Multiple choice vs. open-ended questions

## Support

For issues or feature requests, check the bot logs in `discord.log` or review the implementation in `cogs/trivia.py`.
