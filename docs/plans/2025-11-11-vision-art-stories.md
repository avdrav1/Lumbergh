# Vision-Based Art Stories Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable Claude vision analysis for artwork stories with persistent database caching to avoid redundant API calls.

**Architecture:** Update `generate_art_story()` to check database cache first, then analyze images with Claude Sonnet vision API, falling back to text-only on failures. Cache persists forever (no expiration).

**Tech Stack:**
- Discord.py 2.5.2
- Anthropic Claude API (claude-3-5-sonnet-20241022 vision model)
- SQLite with aiosqlite
- aiohttp for image downloads
- base64 for image encoding

---

## Task 1: Add Database Schema

**Files:**
- Modify: `database/schema.sql` (append at end)

**Step 1: Add art_analysis_cache table**

Open `database/schema.sql` and append:

```sql
CREATE TABLE IF NOT EXISTS `art_analysis_cache` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `artwork_url` TEXT NOT NULL UNIQUE,
  `image_url` TEXT NOT NULL,
  `artwork_title` TEXT,
  `artist` TEXT,
  `museum` TEXT,
  `vision_story` TEXT NOT NULL,
  `analysis_model` varchar(50) DEFAULT 'claude-3-5-sonnet-20241022',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_used_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artwork_url ON art_analysis_cache(artwork_url);
```

**Step 2: Verify schema syntax**

Run: `sqlite3 database/database.db < database/schema.sql`
Expected: No errors (table already exists warnings are OK)

**Step 3: Commit**

```bash
git add database/schema.sql
git commit -m "feat(art): add art_analysis_cache table for vision analysis caching"
```

---

## Task 2: Add Database Methods

**Files:**
- Modify: `database/__init__.py` (append before end of DatabaseManager class)

**Step 1: Add get_cached_art_analysis method**

Add to DatabaseManager class (around line 1457, after `get_user_art_favorites`):

```python
async def get_cached_art_analysis(self, artwork_url: str) -> dict:
    """
    Get cached art analysis for an artwork.

    :param artwork_url: The museum URL for the artwork.
    :return: Dictionary with cached data or None if not found.
    """
    rows = await self.connection.execute(
        "SELECT id, image_url, artwork_title, artist, museum, vision_story, analysis_model, created_at, last_used_at FROM art_analysis_cache WHERE artwork_url=?",
        (artwork_url,),
    )
    async with rows as cursor:
        result = await cursor.fetchone()
        if result:
            return {
                "id": result[0],
                "image_url": result[1],
                "artwork_title": result[2],
                "artist": result[3],
                "museum": result[4],
                "vision_story": result[5],
                "analysis_model": result[6],
                "created_at": result[7],
                "last_used_at": result[8],
            }
        return None
```

**Step 2: Add save_art_analysis method**

```python
async def save_art_analysis(
    self,
    artwork_url: str,
    image_url: str,
    artwork_title: str,
    artist: str,
    museum: str,
    vision_story: str,
) -> int:
    """
    Save artwork analysis to cache.

    :param artwork_url: Museum URL for the artwork (unique key).
    :param image_url: URL of the artwork image.
    :param artwork_title: Title of the artwork.
    :param artist: Artist name.
    :param museum: Museum name.
    :param vision_story: Generated vision story.
    :return: The cache entry ID.
    """
    cursor = await self.connection.execute(
        "INSERT OR REPLACE INTO art_analysis_cache (artwork_url, image_url, artwork_title, artist, museum, vision_story) VALUES (?, ?, ?, ?, ?, ?)",
        (artwork_url, image_url, artwork_title, artist, museum, vision_story),
    )
    await self.connection.commit()
    return cursor.lastrowid
```

**Step 3: Add update_last_used method**

```python
async def update_art_analysis_last_used(self, artwork_url: str) -> None:
    """
    Update the last_used_at timestamp for a cached analysis.

    :param artwork_url: Museum URL for the artwork.
    """
    await self.connection.execute(
        "UPDATE art_analysis_cache SET last_used_at=CURRENT_TIMESTAMP WHERE artwork_url=?",
        (artwork_url,),
    )
    await self.connection.commit()
```

**Step 4: Verify syntax**

Run: `python -m py_compile database/__init__.py`
Expected: No output (successful compilation)

**Step 5: Commit**

```bash
git add database/__init__.py
git commit -m "feat(art): add database methods for art analysis caching"
```

---

## Task 3: Update generate_art_story() Function

**Files:**
- Modify: `cogs/art.py` (replace generate_art_story function around line 200-248)

**Step 1: Import base64 at top of file**

Add to imports section (around line 7):

```python
import base64
```

**Step 2: Replace generate_art_story() function**

Replace the entire `generate_art_story()` function (lines ~200-248) with:

```python
async def generate_art_story(self, artwork: Dict) -> str:
    """
    Generate an engaging story about the artwork using Claude vision analysis.

    Uses cached analysis if available, otherwise analyzes with Claude vision.
    Falls back to text-only if vision fails.

    :param artwork: Dictionary containing artwork information.
    :return: Generated story text.
    """
    artwork_url = artwork.get('object_url', '')

    # Check cache first
    if artwork_url:
        cached = await self.bot.database.get_cached_art_analysis(artwork_url)
        if cached:
            self.bot.logger.info(f"Cache hit for artwork: {artwork['title']}")
            await self.bot.database.update_art_analysis_last_used(artwork_url)
            return cached['vision_story']

    # Attempt vision analysis
    self.bot.logger.info(f"Generating vision analysis for: {artwork['title']}")

    image_url = artwork.get('image_url')
    if image_url and self.client:
        try:
            # Download and encode image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=15) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        image_base64 = base64.b64encode(image_data).decode('utf-8')

                        # Determine media type
                        content_type = response.headers.get('Content-Type', 'image/jpeg')
                        if 'png' in content_type:
                            media_type = "image/png"
                        elif 'webp' in content_type:
                            media_type = "image/webp"
                        elif 'gif' in content_type:
                            media_type = "image/gif"
                        else:
                            media_type = "image/jpeg"

                        # Create enhanced vision prompt
                        prompt = f"""You are analyzing this artwork to create an engaging educational story for a Discord community.

ARTWORK METADATA:
- Title: {artwork['title']}
- Artist: {artwork['artist']}
- Date: {artwork['date']}
- Medium: {artwork['medium']}
- Culture: {artwork.get('culture', 'Unknown')}
- Museum: {artwork['museum']}

Using BOTH what you see in the image AND the metadata above, write 2-3 short paragraphs (max 300 words) that:

1. **Visual Description**: Briefly describe what you see (subjects, colors, composition, mood)
2. **Context & Significance**: Connect the visual elements to historical/cultural context
3. **Engagement Hook**: End with a thought-provoking question or observation that sparks discussion

Tone: Conversational and enthusiastic, not academic. Make people excited to look closely at the artwork and discuss it.

Focus on what makes this piece interesting or unique visually and historically."""

                        # Call Claude vision API
                        message = await self.client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=600,
                            messages=[{
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": media_type,
                                            "data": image_base64
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": prompt
                                    }
                                ]
                            }]
                        )

                        vision_story = f"📚 **Story & Context:**\n\n{message.content[0].text.strip()}"

                        # Cache the result
                        if artwork_url:
                            try:
                                await self.bot.database.save_art_analysis(
                                    artwork_url,
                                    image_url,
                                    artwork['title'],
                                    artwork['artist'],
                                    artwork['museum'],
                                    vision_story
                                )
                                self.bot.logger.info(f"Cached vision analysis for: {artwork['title']}")
                            except Exception as e:
                                self.bot.logger.error(f"Failed to save analysis to cache: {e}")

                        return vision_story

        except Exception as e:
            self.bot.logger.warning(f"Vision analysis failed for {artwork['title']}: {e}")

    # Fallback to text-only generation
    self.bot.logger.info(f"Using text-only fallback for: {artwork['title']}")

    fallback_story = f"📚 **About this artwork:**\n\n"
    fallback_story += f"Created by {artwork['artist']} in {artwork['date']}, "
    fallback_story += f"this {artwork['medium'].lower()} is part of the {artwork['museum']} collection."

    if artwork.get('culture'):
        fallback_story += f" It originates from {artwork['culture']}."

    fallback_story += f"\n\nThis piece represents {artwork['medium'].lower()} artistry from the {artwork['date']} period."

    # Cache text-only fallback
    if artwork_url and self.client:
        try:
            await self.bot.database.save_art_analysis(
                artwork_url,
                image_url or '',
                artwork['title'],
                artwork['artist'],
                artwork['museum'],
                fallback_story
            )
        except Exception as e:
            self.bot.logger.error(f"Failed to save fallback to cache: {e}")

    return fallback_story
```

**Step 3: Verify syntax**

Run: `python -m py_compile cogs/art.py`
Expected: No output (successful compilation)

**Step 4: Commit**

```bash
git add cogs/art.py
git commit -m "feat(art): implement vision-based story generation with caching

- Download and analyze artwork images with Claude Sonnet vision
- Cache analysis results in database (persistent across restarts)
- Fallback to text-only on vision failures
- Update last_used_at on cache hits"
```

---

## Task 4: Test the Implementation

**Step 1: Restart the bot**

Run: `python bot.py`
Expected: Bot starts without errors, art cog loads successfully

**Step 2: Test first artwork (cache miss)**

In Discord: `/art-admin now`

Expected output in logs:
```
[INFO] Generating vision analysis for: [Artwork Title]
[INFO] Cached vision analysis for: [Artwork Title]
```

Expected in Discord:
- ✅ Artwork Posted! message
- Artwork appears in configured channel with vision-generated story

**Step 3: Test second request (cache hit)**

In Discord: `/art-admin now` (run again immediately)

Expected output in logs:
```
[INFO] Cache hit for artwork: [Artwork Title]
```

Expected result: Nearly instant response (< 1 second vs 5-10 seconds)

**Step 4: Verify database**

Run: `sqlite3 database/database.db "SELECT artwork_title, artist, museum, analysis_model FROM art_analysis_cache;"`

Expected: Shows cached artwork with model version

**Step 5: Test fallback (optional)**

Temporarily break vision by setting invalid API key, run `/art-admin now`

Expected:
- Warning in logs about vision failure
- Text-only story posted successfully
- Bot doesn't crash

---

## Task 5: Final Verification

**Step 1: Check all features work**

- ✅ Daily art posts use vision analysis
- ✅ `/art-admin now` generates vision stories
- ✅ Cache persists across bot restarts
- ✅ Fallback works when vision fails
- ✅ No duplicate analyses for same artwork

**Step 2: Review logs for errors**

Run: `tail -50 discord.log`
Expected: No ERROR level messages, only INFO/WARNING

**Step 3: Final commit**

```bash
git add -A
git commit -m "test: verify vision art stories implementation

- Confirmed cache hit/miss behavior
- Verified fallback mechanism
- Tested database persistence
- All features working as designed"
```

---

## Success Criteria Checklist

- [x] Database schema added without errors
- [x] Database methods compile and work
- [x] First artwork analyzed with vision (~5-10 seconds)
- [x] Second request for same artwork instant (<1 second)
- [x] Vision failures gracefully fall back to text
- [x] Cache persists across bot restarts
- [x] Stories describe visual elements
- [x] No errors in production logs

---

## Notes for Engineer

**Testing Tips:**
- Use `/art-admin now` for quick testing (don't wait for scheduled posts)
- Check `discord.log` for detailed execution flow
- Cache key is `artwork['object_url']` (museum's permanent URL)
- Vision analysis costs ~$0.01-0.02 per artwork
- Text-only fallback costs near-zero

**Troubleshooting:**
- If image download fails: Check museum API connectivity
- If vision fails: Verify ANTHROPIC_API_KEY is set correctly
- If cache not working: Check database file permissions
- If bot crashes: Check all imports are present (base64, aiohttp)

**Performance:**
- First analysis: 5-10 seconds (vision processing)
- Cache hit: <1 second (database lookup)
- Fallback: <1 second (text generation)
