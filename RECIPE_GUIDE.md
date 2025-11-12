# Recipe Generator Guide

## Overview
The recipe generator feature uses Claude AI to create personalized recipes based on your preferences, dietary restrictions, and available ingredients.

## Commands

### `/recipe [cuisine] [dietary] [difficulty]`
Generate a random recipe with optional filters.

**Parameters:**
- `cuisine` (optional): Italian, Mexican, Chinese, Japanese, Indian, Thai, French, Mediterranean, American, Korean, or Random
- `dietary` (optional): None, Vegetarian, Vegan, Gluten-Free, Dairy-Free, Keto, Paleo, Low-Carb
- `difficulty` (optional): Easy, Medium, Hard

**Examples:**
```
/recipe
/recipe italian vegetarian medium
/recipe mexican easy
/recipe thai vegan hard
```

**Features:**
- Generates unique recipes using Claude AI
- Shows truncated version with "Show Full Recipe" button for long recipes
- "Save Recipe" button to add to your personal collection
- 5-second cooldown per user

---

### `/recipe-from <ingredients>`
Generate a recipe from ingredients you have available.

**Parameters:**
- `ingredients`: Comma-separated list of ingredients

**Examples:**
```
/recipe-from chicken, rice, broccoli
/recipe-from pasta, tomatoes, garlic, olive oil
/recipe-from eggs, cheese, spinach, mushrooms
```

**Features:**
- AI generates creative recipes based on your available ingredients
- May suggest additional common pantry items
- Same save functionality as `/recipe`

---

### `/recipe-book [page]`
View your saved recipes with pagination.

**Parameters:**
- `page` (optional): Page number (default: 1)

**Features:**
- Shows 5 recipes per page
- Displays recipe ID, cuisine type, difficulty, and dietary info
- Use recipe IDs with `/recipe-delete` to remove recipes

**Example:**
```
/recipe-book
/recipe-book 2
```

---

### `/recipe-delete <recipe_id>`
Delete a saved recipe from your collection.

**Parameters:**
- `recipe_id`: The ID shown in `/recipe-book`

**Example:**
```
/recipe-delete 5
```

---

### `/recipe-daily-setup` (Admin Only)
Configure automated daily recipe posts for your server.

**Parameters:**
- `channel`: Channel to post recipes in
- `post_time`: Time to post in HH:MM format (24-hour)
- `timezone_offset`: Offset from UTC (e.g., -5 for EST, +1 for CET)
- `cuisine` (optional): Preferred cuisine type
- `dietary` (optional): Preferred dietary restriction

**Examples:**
```
/recipe-daily-setup channel:#food-recipes post_time:14:30 timezone_offset:-5
/recipe-daily-setup channel:#general post_time:09:00 timezone_offset:0 cuisine:italian
/recipe-daily-setup channel:#cooking post_time:18:00 timezone_offset:-8 dietary:vegetarian
```

**Features:**
- Bot checks every 15 minutes for scheduled posts
- Posts once per day at configured time
- Uses server's cuisine/dietary preferences
- Requires Administrator permission

---

### `/recipe-daily-disable` (Admin Only)
Turn off daily recipe posts for your server.

**Example:**
```
/recipe-daily-disable
```

---

## User Experience

### Recipe Display
1. **Initial View:**
   - Recipe name and description
   - Metadata (servings, prep time, cook time, difficulty)
   - Truncated ingredients list
   - "Show Full Recipe" button (if recipe is long)
   - "Save Recipe" button

2. **Expanded View:**
   - Complete ingredients list with measurements
   - Step-by-step instructions
   - Chef's tips
   - "Show Less" button to collapse

3. **Saved Confirmation:**
   - Ephemeral message (only you see it)
   - Button changes to "✅ Saved!" and is disabled
   - Recipe ID provided for reference

### Personal Recipe Collection
- Recipes are saved **per user** (not server-wide)
- Access your collection from any server with the bot
- Each recipe includes cuisine, dietary, and difficulty tags
- Pagination for easy browsing

### Daily Posts
- Automated posts at configured times
- Full recipe displayed immediately (no truncation)
- Recipes match server's preferences
- Footer encourages users to try `/recipe` command

---

## Technical Details

### Database Tables

**saved_recipes:**
- User-specific recipe storage
- Includes recipe data as JSON
- Metadata fields for filtering (cuisine, dietary, difficulty)

**recipe_daily_config:**
- Per-server daily post configuration
- Channel, time, timezone, preferences
- Tracks last post date to prevent duplicates

### AI Generation
- Uses Claude 3.5 Haiku for fast, cost-effective generation
- Structured prompts ensure consistent formatting
- Fallback to pre-made recipes if API fails
- ~$0.01-0.02 per recipe generated

### Background Tasks
- Checks every 15 minutes for scheduled posts
- Posts within 15-minute window of configured time
- Verifies channel permissions before posting
- Updates last post date after successful posting

---

## Troubleshooting

### "Recipe Generation Failed"
- Claude API key may be missing or invalid
- Check `ANTHROPIC_API_KEY` in `.env` file
- Bot falls back to pre-made recipes if AI unavailable

### Daily Posts Not Working
- Verify bot has permissions in target channel:
  - Send Messages
  - Embed Links
- Check time and timezone offset are correct
- Review bot logs for errors

### Can't Save Recipe
- Database connection issue
- Check `database/database.db` exists and is writable
- Review bot logs for specific error

---

## Cost Considerations

- **Per recipe**: ~$0.01-0.02 (1,500-2,000 tokens)
- **Daily posts**: ~$0.30-0.60/month per server (assuming 1 post/day)
- **User cooldown**: 5 seconds prevents spam
- **Efficient model**: Uses Claude 3.5 Haiku (fast + cheap)

With 100 active users generating 10 recipes each per month:
- **Total cost**: ~$10-20/month
- **Plus daily posts**: +$0.30-0.60 per configured server

---

## Examples of Generated Recipes

The AI generates creative, practical recipes like:
- "Creamy Tuscan Garlic Shrimp" (Italian, easy)
- "Spicy Korean Beef Bulgogi Bowl" (Korean, medium)
- "One-Pan Lemon Herb Chicken with Roasted Vegetables" (Mediterranean, easy)
- "Vegan Thai Green Curry with Tofu" (Thai, vegan, medium)
- "Keto Bacon-Wrapped Jalapeño Poppers" (American, keto, easy)

Each includes:
- Specific measurements
- Clear step-by-step instructions
- Helpful cooking tips
- Reasonable ingredient counts (5-12 items)
- Practical for home cooking

---

## Future Enhancements (Not Implemented)

Potential features for future development:
- `/recipe-search <query>` - Search your saved recipes
- `/recipe-share` - Share recipes with the server
- Rating system with ⭐ reactions
- Nutrition information
- Recipe categories and tags
- Shopping list generation
- Image generation for recipes (DALL-E integration)
- Recipe remixing (variations on saved recipes)
- Collaborative cookbooks (server-wide collections)
