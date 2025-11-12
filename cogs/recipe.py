"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import os
import sys
import json
import random
from datetime import datetime, time, timedelta
from typing import Optional, Dict

import discord
from anthropic import AsyncAnthropic
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context

# Import helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers.claude_cog import ClaudeAICog


class ExpandableRecipeView(discord.ui.View):
    """View with buttons to expand/collapse recipes and save them."""

    def __init__(self, full_text: str, truncated_text: str, recipe_data: Dict, user_id: int, cog):
        super().__init__(timeout=None)  # Persistent view
        self.full_text = full_text
        self.truncated_text = truncated_text
        self.recipe_data = recipe_data
        self.user_id = user_id
        self.cog = cog
        self.expanded = False
        self.saved = False

    @discord.ui.button(label="📖 Show Full Recipe", style=discord.ButtonStyle.primary, custom_id="expand_recipe")
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle between expanded and collapsed view."""
        self.expanded = not self.expanded

        # Create new embed
        embed = discord.Embed(
            title=f"🍳 {self.recipe_data['name']}",
            description=self.full_text if self.expanded else self.truncated_text,
            color=0x2ecc71,
        )

        # Add metadata fields
        metadata = []
        if self.recipe_data.get('servings'):
            metadata.append(f"📊 Servings: {self.recipe_data['servings']}")
        if self.recipe_data.get('prep_time'):
            metadata.append(f"⏱️ Prep: {self.recipe_data['prep_time']}")
        if self.recipe_data.get('cook_time'):
            metadata.append(f"🔥 Cook: {self.recipe_data['cook_time']}")
        if self.recipe_data.get('difficulty'):
            metadata.append(f"📈 Difficulty: {self.recipe_data['difficulty'].title()}")

        if metadata:
            embed.add_field(name="Info", value=" | ".join(metadata), inline=False)

        if self.expanded:
            button.label = "📖 Show Less"
            button.style = discord.ButtonStyle.secondary
        else:
            button.label = "📖 Show Full Recipe"
            button.style = discord.ButtonStyle.primary

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="💾 Save Recipe", style=discord.ButtonStyle.success, custom_id="save_recipe")
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Save the recipe to user's collection."""
        if self.saved:
            await interaction.response.send_message(
                "You've already saved this recipe! Use `/recipe-manage book` to view your collection.",
                ephemeral=True
            )
            return

        try:
            # Save to database
            recipe_id = await self.cog.bot.database.save_recipe(
                user_id=interaction.user.id,
                recipe_name=self.recipe_data['name'],
                recipe_data=json.dumps(self.recipe_data),
                cuisine=self.recipe_data.get('cuisine'),
                dietary=self.recipe_data.get('dietary'),
                difficulty=self.recipe_data.get('difficulty')
            )

            self.saved = True
            button.label = "✅ Saved!"
            button.disabled = True

            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                f"✅ Recipe saved! Use `/recipe-manage book` to view your collection. (Recipe ID: {recipe_id})",
                ephemeral=True
            )

        except Exception as e:
            self.cog.bot.logger.error(f"Error saving recipe: {e}")
            await interaction.response.send_message(
                "❌ Failed to save recipe. Please try again later.",
                ephemeral=True
            )


class Recipe(ClaudeAICog, name="recipe"):
    # Class-level constants for command choices
    CUISINES = [
        "Italian", "Mexican", "Chinese", "Japanese", "Indian",
        "Thai", "French", "Mediterranean", "American", "Korean"
    ]

    DIETARY = [
        "None", "Vegetarian", "Vegan", "Gluten-Free",
        "Dairy-Free", "Keto", "Paleo", "Low-Carb"
    ]

    DIFFICULTY = ["Easy", "Medium", "Hard"]

    def __init__(self, bot) -> None:
        super().__init__(bot, cog_name="Recipe cog")
        self.check_daily_recipes.start()

        # Fallback recipes
        self.FALLBACK_RECIPES = [
            {
                "name": "Classic Spaghetti Carbonara",
                "description": "A creamy Italian pasta dish with eggs, cheese, and pancetta.",
                "servings": "4",
                "prep_time": "10 min",
                "cook_time": "20 min",
                "difficulty": "medium",
                "cuisine": "Italian",
                "dietary": "none",
                "ingredients": [
                    "400g spaghetti",
                    "200g pancetta or guanciale, diced",
                    "4 large eggs",
                    "100g Pecorino Romano cheese, grated",
                    "Black pepper to taste",
                    "Salt for pasta water"
                ],
                "instructions": [
                    "Bring a large pot of salted water to boil and cook spaghetti until al dente.",
                    "Meanwhile, cook pancetta in a large skillet over medium heat until crispy.",
                    "In a bowl, whisk together eggs and cheese.",
                    "Drain pasta, reserving 1 cup pasta water.",
                    "Add hot pasta to the pancetta pan, remove from heat.",
                    "Quickly stir in egg mixture, adding pasta water as needed for creaminess.",
                    "Season generously with black pepper and serve immediately."
                ],
                "tips": "The key is to work quickly and off heat when adding eggs to prevent scrambling!"
            }
        ]

    def cog_unload(self) -> None:
        """Clean up when cog is unloaded."""
        self.check_daily_recipes.cancel()

    async def generate_recipe(
        self,
        cuisine: str = "random",
        dietary: str = "none",
        difficulty: str = "medium",
        ingredients: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Generate a recipe using Claude AI.

        :param cuisine: The cuisine type.
        :param dietary: Dietary restrictions.
        :param difficulty: Difficulty level.
        :param ingredients: Optional ingredients to base the recipe on.
        :return: Dictionary with recipe data or None if failed.
        """
        if not self.client:
            return random.choice(self.FALLBACK_RECIPES)

        # Build prompt based on parameters
        if ingredients:
            base_prompt = f"Generate a {difficulty} difficulty recipe using these ingredients: {ingredients}."
        else:
            cuisine_str = f"{cuisine} cuisine" if cuisine != "random" else "any cuisine"
            base_prompt = f"Generate a {difficulty} difficulty {cuisine_str} recipe."

        dietary_str = ""
        if dietary and dietary.lower() != "none":
            dietary_str = f" The recipe must be {dietary}."

        prompt = f"""{base_prompt}{dietary_str}

Format your response EXACTLY like this:
RECIPE_NAME: [creative recipe name]
DESCRIPTION: [one sentence description]
SERVINGS: [number]
PREP_TIME: [X min]
COOK_TIME: [X min]
DIFFICULTY: {difficulty}
INGREDIENTS:
- [ingredient 1 with amount]
- [ingredient 2 with amount]
- [ingredient 3 with amount]
INSTRUCTIONS:
1. [step 1]
2. [step 2]
3. [step 3]
TIPS: [one helpful cooking tip]

Rules:
- Be specific with measurements
- Instructions should be clear and actionable
- Keep ingredients list reasonable (5-12 items)
- Make it practical for home cooking"""

        try:
            message = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            response = message.content[0].text.strip()

            # Parse the response
            recipe_data = {
                "name": "",
                "description": "",
                "servings": "",
                "prep_time": "",
                "cook_time": "",
                "difficulty": difficulty,
                "cuisine": cuisine if cuisine != "random" else "Mixed",
                "dietary": dietary,
                "ingredients": [],
                "instructions": [],
                "tips": ""
            }

            current_section = None
            for line in response.split('\n'):
                line = line.strip()
                if not line:
                    continue

                if line.startswith('RECIPE_NAME:'):
                    recipe_data['name'] = line.replace('RECIPE_NAME:', '').strip()
                elif line.startswith('DESCRIPTION:'):
                    recipe_data['description'] = line.replace('DESCRIPTION:', '').strip()
                elif line.startswith('SERVINGS:'):
                    recipe_data['servings'] = line.replace('SERVINGS:', '').strip()
                elif line.startswith('PREP_TIME:'):
                    recipe_data['prep_time'] = line.replace('PREP_TIME:', '').strip()
                elif line.startswith('COOK_TIME:'):
                    recipe_data['cook_time'] = line.replace('COOK_TIME:', '').strip()
                elif line.startswith('DIFFICULTY:'):
                    recipe_data['difficulty'] = line.replace('DIFFICULTY:', '').strip()
                elif line.startswith('INGREDIENTS:'):
                    current_section = 'ingredients'
                elif line.startswith('INSTRUCTIONS:'):
                    current_section = 'instructions'
                elif line.startswith('TIPS:'):
                    recipe_data['tips'] = line.replace('TIPS:', '').strip()
                    current_section = None
                elif current_section == 'ingredients' and line.startswith('-'):
                    recipe_data['ingredients'].append(line[1:].strip())
                elif current_section == 'instructions':
                    # Remove number prefix if present
                    if line[0].isdigit() and '. ' in line:
                        line = line.split('. ', 1)[1]
                    recipe_data['instructions'].append(line)

            # Validate we got essential parts
            if not recipe_data['name'] or not recipe_data['ingredients'] or not recipe_data['instructions']:
                raise ValueError("Failed to parse AI response")

            return recipe_data

        except Exception as e:
            self.bot.logger.error(f"Error generating recipe: {e}")
            return random.choice(self.FALLBACK_RECIPES)

    def format_recipe(self, recipe_data: Dict, full: bool = False) -> str:
        """
        Format recipe data into a Discord-friendly string.

        :param recipe_data: Dictionary with recipe data.
        :param full: If True, return full recipe. If False, return truncated version.
        :return: Formatted recipe string.
        """
        parts = []

        # Description
        if recipe_data.get('description'):
            parts.append(recipe_data['description'])
            parts.append("")

        # Ingredients
        parts.append("🥘 **Ingredients**")
        for ing in recipe_data['ingredients']:
            parts.append(f"• {ing}")
        parts.append("")

        # Instructions
        parts.append("📝 **Instructions**")
        for i, inst in enumerate(recipe_data['instructions'], 1):
            parts.append(f"{i}. {inst}")

        # Tips
        if recipe_data.get('tips'):
            parts.append("")
            parts.append(f"💡 **Chef's Tip:** {recipe_data['tips']}")

        full_text = "\n".join(parts)

        if not full and len(full_text) > 800:
            # Truncate for initial display
            truncated_parts = []
            truncated_parts.append(recipe_data.get('description', ''))
            truncated_parts.append("")
            truncated_parts.append("🥘 **Ingredients**")
            for ing in recipe_data['ingredients'][:5]:
                truncated_parts.append(f"• {ing}")
            if len(recipe_data['ingredients']) > 5:
                truncated_parts.append(f"• *...and {len(recipe_data['ingredients']) - 5} more ingredients*")
            truncated_parts.append("")
            truncated_parts.append("*⬇️ Click 'Show Full Recipe' below to see instructions*")
            return "\n".join(truncated_parts), full_text

        return full_text, full_text

    @commands.hybrid_command(
        name="recipe",
        description="Generate a recipe with optional filters",
    )
    @app_commands.describe(
        cuisine="Type of cuisine (default: random)",
        dietary="Dietary restrictions (default: none)",
        difficulty="Difficulty level (default: medium)"
    )
    @app_commands.choices(
        cuisine=[app_commands.Choice(name=c, value=c.lower()) for c in ["Random"] + CUISINES],
        dietary=[app_commands.Choice(name=d, value=d.lower()) for d in DIETARY],
        difficulty=[app_commands.Choice(name=d, value=d.lower()) for d in DIFFICULTY]
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def recipe(
        self,
        context: Context,
        cuisine: Optional[str] = "random",
        dietary: Optional[str] = "none",
        difficulty: Optional[str] = "medium"
    ) -> None:
        """
        Generate a recipe using Claude AI with optional filters.

        :param context: The hybrid command context.
        :param cuisine: Type of cuisine.
        :param dietary: Dietary restrictions.
        :param difficulty: Difficulty level.
        """
        # Defer response since AI generation takes time
        if context.interaction:
            await context.defer()

        # Generate recipe
        recipe_data = await self.generate_recipe(cuisine, dietary, difficulty)

        if not recipe_data:
            embed = discord.Embed(
                title="❌ Recipe Generation Failed",
                description="Failed to generate recipe. Please try again.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Format recipe
        truncated_text, full_text = self.format_recipe(recipe_data)

        # Create embed
        embed = discord.Embed(
            title=f"🍳 {recipe_data['name']}",
            description=truncated_text,
            color=0x2ecc71
        )

        # Add metadata
        metadata = []
        if recipe_data.get('servings'):
            metadata.append(f"📊 Servings: {recipe_data['servings']}")
        if recipe_data.get('prep_time'):
            metadata.append(f"⏱️ Prep: {recipe_data['prep_time']}")
        if recipe_data.get('cook_time'):
            metadata.append(f"🔥 Cook: {recipe_data['cook_time']}")
        if recipe_data.get('difficulty'):
            metadata.append(f"📈 Difficulty: {recipe_data['difficulty'].title()}")

        if metadata:
            embed.add_field(name="Info", value=" | ".join(metadata), inline=False)

        # Add view with buttons if recipe is long
        if len(full_text) > 800:
            view = ExpandableRecipeView(full_text, truncated_text, recipe_data, context.author.id, self)
            await context.send(embed=embed, view=view)
        else:
            # Recipe is short, just add save button
            view = ExpandableRecipeView(full_text, full_text, recipe_data, context.author.id, self)
            # Remove expand button since recipe is already shown in full
            view.children[0].disabled = True
            view.children[0].style = discord.ButtonStyle.secondary
            await context.send(embed=embed, view=view)

    @commands.hybrid_command(
        name="recipe-from",
        description="Generate a recipe from ingredients you have",
    )
    @app_commands.describe(
        ingredients="Comma-separated list of ingredients (e.g., 'chicken, rice, broccoli')"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def recipe_from(self, context: Context, *, ingredients: str) -> None:
        """
        Generate a recipe based on ingredients you have.

        :param context: The hybrid command context.
        :param ingredients: Comma-separated ingredients.
        """
        if context.interaction:
            await context.defer()

        # Generate recipe from ingredients
        recipe_data = await self.generate_recipe(ingredients=ingredients)

        if not recipe_data:
            embed = discord.Embed(
                title="❌ Recipe Generation Failed",
                description="Failed to generate recipe from those ingredients. Please try again.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Format and send
        truncated_text, full_text = self.format_recipe(recipe_data)

        embed = discord.Embed(
            title=f"🍳 {recipe_data['name']}",
            description=truncated_text,
            color=0x2ecc71
        )

        metadata = []
        if recipe_data.get('servings'):
            metadata.append(f"📊 Servings: {recipe_data['servings']}")
        if recipe_data.get('prep_time'):
            metadata.append(f"⏱️ Prep: {recipe_data['prep_time']}")
        if recipe_data.get('cook_time'):
            metadata.append(f"🔥 Cook: {recipe_data['cook_time']}")

        if metadata:
            embed.add_field(name="Info", value=" | ".join(metadata), inline=False)

        view = ExpandableRecipeView(full_text, truncated_text, recipe_data, context.author.id, self)
        await context.send(embed=embed, view=view)

    @commands.hybrid_command(
        name="recipe-manage",
        description="Manage recipes and daily recipe settings",
    )
    @app_commands.describe(
        action="Management action to perform",
        page="[book] Page number (default: 1)",
        recipe_id="[delete] Recipe ID to delete",
        channel="[daily-setup] Channel for daily posts",
        post_time="[daily-setup] Post time in HH:MM format (24-hour)",
        timezone_offset="[daily-setup] Timezone offset from UTC (e.g., -5 for EST)",
        cuisine="[daily-setup] Preferred cuisine (optional)",
        dietary="[daily-setup] Preferred dietary restriction (optional)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="View Recipe Book", value="book"),
            app_commands.Choice(name="Delete Recipe", value="delete"),
            app_commands.Choice(name="Setup Daily Posts", value="daily-setup"),
            app_commands.Choice(name="Disable Daily Posts", value="daily-disable")
        ],
        cuisine=[app_commands.Choice(name=c, value=c.lower()) for c in ["Random"] + CUISINES],
        dietary=[app_commands.Choice(name=d, value=d.lower()) for d in DIETARY]
    )
    async def recipe_manage(
        self,
        context: Context,
        action: str,
        page: Optional[int] = 1,
        recipe_id: Optional[int] = None,
        channel: Optional[discord.TextChannel] = None,
        post_time: Optional[str] = None,
        timezone_offset: Optional[int] = 0,
        cuisine: Optional[str] = "random",
        dietary: Optional[str] = "none"
    ) -> None:
        """
        Manage recipes and daily recipe settings.

        :param context: The hybrid command context.
        :param action: The management action to perform.
        :param page: Page number for book view.
        :param recipe_id: Recipe ID for deletion.
        :param channel: Channel for daily posts.
        :param post_time: Time for daily posts.
        :param timezone_offset: Timezone offset for daily posts.
        :param cuisine: Cuisine preference for daily posts.
        :param dietary: Dietary preference for daily posts.
        """
        if action == "book":
            await self._manage_book(context, page)
        elif action == "delete":
            await self._manage_delete(context, recipe_id)
        elif action == "daily-setup":
            await self._manage_daily_setup(context, channel, post_time, timezone_offset, cuisine, dietary)
        elif action == "daily-disable":
            await self._manage_daily_disable(context)
        else:
            embed = discord.Embed(
                title="❌ Invalid Action",
                description="Please select a valid management action.",
                color=0xE02B2B
            )
            await context.send(embed=embed)

    async def _manage_book(self, context: Context, page: int = 1) -> None:
        """
        View saved recipes with pagination.

        :param context: The hybrid command context.
        :param page: Page number.
        """
        page = max(1, page)  # Ensure page is at least 1
        offset = (page - 1) * 5

        # Get user's recipes
        recipes = await self.bot.database.get_user_recipes(context.author.id, limit=5, offset=offset)
        total_recipes = await self.bot.database.count_user_recipes(context.author.id)

        if total_recipes == 0:
            embed = discord.Embed(
                title="📚 Your Recipe Book",
                description="You haven't saved any recipes yet!\n\nUse `/recipe` to generate recipes and save your favorites.",
                color=0x3498db
            )
            await context.send(embed=embed)
            return

        # Create embed
        total_pages = (total_recipes + 4) // 5  # Ceiling division
        embed = discord.Embed(
            title="📚 Your Recipe Book",
            description=f"You have {total_recipes} saved recipe{'s' if total_recipes != 1 else ''}",
            color=0x2ecc71
        )

        for recipe in recipes:
            recipe_data = json.loads(recipe['recipe_data'])
            metadata = []
            if recipe.get('cuisine'):
                metadata.append(recipe['cuisine'].title())
            if recipe.get('difficulty'):
                metadata.append(recipe['difficulty'].title())
            if recipe.get('dietary') and recipe['dietary'] != 'none':
                metadata.append(recipe['dietary'].title())

            value = f"ID: `{recipe['id']}`"
            if metadata:
                value += f" | {' • '.join(metadata)}"

            embed.add_field(
                name=f"🍳 {recipe['recipe_name']}",
                value=value,
                inline=False
            )

        embed.set_footer(text=f"Page {page}/{total_pages} • Use /recipe-manage delete to remove recipes")

        await context.send(embed=embed)

    async def _manage_delete(self, context: Context, recipe_id: Optional[int]) -> None:
        """
        Delete a recipe from user's collection.

        :param context: The hybrid command context.
        :param recipe_id: ID of the recipe to delete.
        """
        if recipe_id is None:
            embed = discord.Embed(
                title="❌ Missing Recipe ID",
                description="Please provide a recipe ID to delete.\n\nUse `/recipe-manage book` to see your recipes and their IDs.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Try to delete
        deleted = await self.bot.database.delete_recipe(context.author.id, recipe_id)

        if deleted:
            embed = discord.Embed(
                title="✅ Recipe Deleted",
                description=f"Recipe #{recipe_id} has been removed from your collection.",
                color=0x2ecc71
            )
        else:
            embed = discord.Embed(
                title="❌ Recipe Not Found",
                description=f"Could not find recipe #{recipe_id} in your collection.",
                color=0xE02B2B
            )

        await context.send(embed=embed)

    async def _manage_daily_setup(
        self,
        context: Context,
        channel: Optional[discord.TextChannel],
        post_time: Optional[str],
        timezone_offset: int,
        cuisine: str,
        dietary: str
    ) -> None:
        """
        Setup daily recipe posts for the server.

        :param context: The hybrid command context.
        :param channel: Channel to post to.
        :param post_time: Time in HH:MM format.
        :param timezone_offset: Timezone offset from UTC.
        :param cuisine: Preferred cuisine.
        :param dietary: Preferred dietary restriction.
        """
        # Check admin permissions
        if not context.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions to setup daily recipes.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Validate required parameters
        if channel is None:
            embed = discord.Embed(
                title="❌ Missing Channel",
                description="Please specify a channel for daily recipe posts.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        if post_time is None:
            embed = discord.Embed(
                title="❌ Missing Post Time",
                description="Please specify a post time in HH:MM format (e.g., 14:30 for 2:30 PM).",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Validate time format
        try:
            time_parts = post_time.split(':')
            if len(time_parts) != 2:
                raise ValueError
            hour, minute = int(time_parts[0]), int(time_parts[1])
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Time Format",
                description="Please use HH:MM format (24-hour), e.g., 14:30 for 2:30 PM",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        # Save configuration
        await self.bot.database.set_recipe_daily_config(
            server_id=context.guild.id,
            channel_id=channel.id,
            post_time=post_time,
            timezone_offset=timezone_offset,
            cuisine_preference=cuisine,
            dietary_preference=dietary
        )

        embed = discord.Embed(
            title="✅ Daily Recipes Configured",
            description=f"Daily recipes will be posted in {channel.mention} at {post_time} (UTC{timezone_offset:+d})",
            color=0x2ecc71
        )

        if cuisine != "random":
            embed.add_field(name="Cuisine", value=cuisine.title(), inline=True)
        if dietary != "none":
            embed.add_field(name="Dietary", value=dietary.title(), inline=True)

        embed.set_footer(text="Use /recipe-manage daily-disable to turn off daily posts")

        await context.send(embed=embed)

    async def _manage_daily_disable(self, context: Context) -> None:
        """
        Disable daily recipe posts for the server.

        :param context: The hybrid command context.
        """
        # Check admin permissions
        if not context.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need administrator permissions to disable daily recipes.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        success = await self.bot.database.toggle_recipe_daily(context.guild.id, False)

        if success:
            embed = discord.Embed(
                title="✅ Daily Recipes Disabled",
                description="Daily recipe posts have been turned off.",
                color=0x2ecc71
            )
        else:
            embed = discord.Embed(
                title="❌ Not Configured",
                description="Daily recipes are not configured for this server.",
                color=0xE02B2B
            )

        await context.send(embed=embed)

    @tasks.loop(minutes=15)
    async def check_daily_recipes(self) -> None:
        """Background task to check for servers needing daily recipe posts."""
        try:
            servers = await self.bot.database.get_servers_needing_recipe_post()

            for server_data in servers:
                server_id = int(server_data[0])
                channel_id = int(server_data[1])
                post_time_str = server_data[2]
                timezone_offset = server_data[3]
                cuisine_pref = server_data[4]
                dietary_pref = server_data[5]
                last_post_date = server_data[6]

                # Parse post time
                hour, minute = map(int, post_time_str.split(':'))
                post_time_obj = time(hour, minute)

                # Get current time in server's timezone
                utc_now = datetime.utcnow()
                server_now = utc_now + timedelta(hours=timezone_offset)
                current_time = server_now.time()
                current_date = server_now.strftime('%Y-%m-%d')

                # Check if we're within 15 minutes of post time
                post_datetime = datetime.combine(server_now.date(), post_time_obj)
                time_diff = abs((server_now - post_datetime).total_seconds() / 60)

                # Post if within 15-minute window and haven't posted today
                if time_diff <= 15 and last_post_date != current_date:
                    await self.post_daily_recipe(server_id, channel_id, cuisine_pref, dietary_pref, current_date)

        except Exception as e:
            self.bot.logger.error(f"Error in daily recipe check: {e}")

    async def post_daily_recipe(self, server_id: int, channel_id: int, cuisine: str, dietary: str, current_date: str) -> None:
        """Post a daily recipe to a channel."""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                self.bot.logger.warning(f"Channel {channel_id} not found for daily recipe")
                return

            # Check permissions
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.send_messages or not permissions.embed_links:
                self.bot.logger.warning(f"Missing permissions in channel {channel_id}")
                return

            # Generate recipe
            recipe_data = await self.generate_recipe(cuisine, dietary, "medium")

            if not recipe_data:
                self.bot.logger.error("Failed to generate daily recipe")
                return

            # Format recipe
            truncated_text, full_text = self.format_recipe(recipe_data)

            # Create embed
            embed = discord.Embed(
                title=f"🍳 Daily Recipe: {recipe_data['name']}",
                description=full_text,
                color=0x2ecc71
            )

            metadata = []
            if recipe_data.get('servings'):
                metadata.append(f"📊 Servings: {recipe_data['servings']}")
            if recipe_data.get('prep_time'):
                metadata.append(f"⏱️ Prep: {recipe_data['prep_time']}")
            if recipe_data.get('cook_time'):
                metadata.append(f"🔥 Cook: {recipe_data['cook_time']}")
            if recipe_data.get('difficulty'):
                metadata.append(f"📈 Difficulty: {recipe_data['difficulty'].title()}")

            if metadata:
                embed.add_field(name="Info", value=" | ".join(metadata), inline=False)

            embed.set_footer(text="Use /recipe to generate more recipes!")

            await channel.send(embed=embed)

            # Update last post date
            await self.bot.database.update_recipe_last_post(server_id, current_date)

            self.bot.logger.info(f"Posted daily recipe to server {server_id}")

        except Exception as e:
            self.bot.logger.error(f"Error posting daily recipe: {e}")

    @check_daily_recipes.before_loop
    async def before_check_daily_recipes(self) -> None:
        """Wait until bot is ready before starting the task."""
        await self.bot.wait_until_ready()


async def setup(bot) -> None:
    await bot.add_cog(Recipe(bot))
