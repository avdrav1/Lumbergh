# Vision-Based Art Stories with Smart Caching

**Date:** 2025-11-11
**Status:** Design Approved
**Implementation:** Pending

## Problem

The `generate_art_story()` function sends only text metadata to Claude, not the actual artwork image. This causes Claude to respond: "I noticed that no image was actually uploaded with your request." Users see the artwork displayed in Discord but get text-only stories that don't describe visual elements.

## Solution

Update the art cog to use Claude's vision API for story generation, with persistent database caching to avoid redundant analysis.

## Design Overview

**Approach:** Option B - Smart Caching with Database Persistence
**Rationale:** Balances quality (vision analysis), cost (never re-analyze), and simplicity (straightforward implementation)

## Database Schema

### New Table: `art_analysis_cache`

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

**Design Decisions:**
- `artwork_url` is unique key (museum's permanent URL)
- Store metadata for debugging/display
- Track analysis model (future-proofing)
- `last_used_at` enables future cleanup if needed
- No automatic expiration (unlimited storage)

### Database Methods

```python
async def get_cached_art_analysis(artwork_url: str) -> dict | None
async def save_art_analysis(artwork_url: str, image_url: str, artwork_data: dict, story: str) -> int
async def update_last_used(artwork_url: str) -> None
```

## Function Flow: `generate_art_story()`

### Updated Signature
```python
async def generate_art_story(self, artwork: Dict) -> str:
    """
    Generate engaging story about artwork using vision analysis.
    Uses cached analysis if available, otherwise analyzes with Claude vision.
    Falls back to text-only if vision fails.
    """
```

### Execution Logic

1. **Cache Lookup**
   - Query database for `artwork['object_url']`
   - If found: Update `last_used_at` and return cached story
   - If not found: Continue to step 2

2. **Vision Analysis**
   - Download image from `artwork['image_url']`
   - Convert to base64
   - Send to Claude Sonnet vision with enhanced prompt
   - Timeout: 15 seconds

3. **On Success**
   - Save story to database cache
   - Return vision-generated story

4. **On Failure**
   - Log warning with error details
   - Fall back to text-only (metadata-based) story
   - Save text-only story to cache
   - Return fallback story

## Vision Prompt

```python
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
```

**Model:** `claude-3-5-sonnet-20241022` (vision-capable)

## Error Handling

### Image Download Failures
- Timeout: 15 seconds (matches existing vision commands)
- Action: Log warning, skip to text-only fallback
- Don't cache failed attempts (retry on next request)

### Vision API Failures
- Catch all exceptions from Claude API
- Log full error for debugging
- Fall back to text-only generation
- Cache the text-only result

### Database Failures
- Cache lookup fails: Continue to vision analysis
- Cache save fails: Log error but still return story
- Don't let cache issues break artwork posting

## Logging Strategy

```python
self.bot.logger.info(f"Cache hit for artwork: {artwork['title']}")
self.bot.logger.info(f"Generating vision analysis for: {artwork['title']}")
self.bot.logger.warning(f"Vision analysis failed for {artwork['title']}: {error}")
self.bot.logger.error(f"Failed to save analysis to cache: {error}")
```

## Implementation Order

1. Add database schema to `schema.sql`
2. Add database methods to `DatabaseManager` (`database/__init__.py`)
3. Update `generate_art_story()` function in `cogs/art.py`
4. Test with `/art-admin now` command
5. Verify caching (second request should be instant)

## Success Criteria

- ✅ First artwork analyzed with vision (~5-10 seconds)
- ✅ Second request for same artwork instant (<1 second)
- ✅ Vision failures gracefully fall back to text
- ✅ Cache persists across bot restarts
- ✅ Stories describe visual elements, not just metadata

## Cost Impact

**Before:** $0 (text-only, Haiku)
**After:** ~$0.01-0.02 per unique artwork (Sonnet vision)
**With caching:** Same artwork analyzed once, reused forever

**Example:** 365 daily posts/year with 50% unique artworks = ~$1.80-3.65/year

## Future Enhancements (Not in Scope)

- Share analysis cache with `/art-analyze` command
- Add admin preview command
- Artwork recommendation system based on analysis
- Periodic cache cleanup (currently unlimited)
