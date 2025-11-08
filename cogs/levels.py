"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context


class Levels(commands.Cog, name="levels"):
    def __init__(self, bot) -> None:
        self.bot = bot

    def _create_progress_bar(self, current: int, required: int, length: int = 10) -> str:
        """
        Create a visual progress bar for XP.

        :param current: Current XP in level.
        :param required: Required XP for next level.
        :param length: Length of the progress bar.
        :return: String representation of progress bar.
        """
        filled = int((current / required) * length) if required > 0 else 0
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}]"

    def _calculate_xp_for_level(self, level: int) -> int:
        """
        Calculate total XP required to reach a specific level.
        Formula: XP = (Level / 0.1)^2

        :param level: The target level.
        :return: Total XP required.
        """
        return int((level / 0.1) ** 2)

    def _get_xp_in_level(self, total_xp: int, current_level: int) -> tuple:
        """
        Get XP progress within current level.

        :param total_xp: User's total XP.
        :param current_level: User's current level.
        :return: Tuple of (current_xp_in_level, xp_required_for_next_level).
        """
        current_level_xp = self._calculate_xp_for_level(current_level)
        next_level_xp = self._calculate_xp_for_level(current_level + 1)
        xp_in_level = total_xp - current_level_xp
        xp_required = next_level_xp - current_level_xp
        return (xp_in_level, xp_required)

    @commands.hybrid_command(
        name="rank",
        description="Show your or another user's rank card with XP and level.",
    )
    @app_commands.describe(user="The user to check (leave empty for yourself)")
    async def rank(self, context: Context, user: discord.Member = None) -> None:
        """
        Display a user's rank card showing their XP, level, rank, and progress.

        :param context: The application command context.
        :param user: The user to check (defaults to command author).
        """
        target_user = user or context.author

        # Prevent checking bots
        if target_user.bot:
            embed = discord.Embed(
                description="Bots don't gain XP!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Get user data
        data = await self.bot.database.get_user_level_data(
            target_user.id, context.guild.id
        )

        if data is None:
            embed = discord.Embed(
                description=f"{'You have' if target_user == context.author else f'{target_user.mention} has'} not gained any XP yet!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Get rank
        rank = await self.bot.database.get_user_rank(target_user.id, context.guild.id)

        # Calculate XP progress in current level
        xp_in_level, xp_required = self._get_xp_in_level(data["xp"], data["level"])
        progress_bar = self._create_progress_bar(xp_in_level, xp_required)

        # Create rank card embed
        embed = discord.Embed(
            title=f"📊 Rank Card - {target_user.display_name}",
            color=0xBEBEFE,
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Level", value=f"**{data['level']}**", inline=True)
        embed.add_field(name="Rank", value=f"**#{rank}**", inline=True)
        embed.add_field(name="Total XP", value=f"**{data['xp']:,}**", inline=True)
        embed.add_field(
            name="Level Progress",
            value=f"{progress_bar}\n{xp_in_level:,} / {xp_required:,} XP",
            inline=False,
        )
        embed.add_field(
            name="Messages", value=f"**{data['total_messages']:,}**", inline=True
        )
        embed.set_footer(text=f"Keep chatting to gain more XP!")

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="leaderboard",
        description="Show the server's XP leaderboard.",
    )
    @app_commands.describe(page="The page number to view (default: 1)")
    async def leaderboard(self, context: Context, page: int = 1) -> None:
        """
        Display the server's XP leaderboard with pagination.

        :param context: The application command context.
        :param page: The page number to display.
        """
        if page < 1:
            page = 1

        # Get leaderboard data
        offset = (page - 1) * 10
        leaderboard = await self.bot.database.get_leaderboard(
            context.guild.id, limit=10, offset=offset
        )

        if not leaderboard:
            embed = discord.Embed(
                description="No one has gained XP yet! Start chatting to appear on the leaderboard.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Create leaderboard embed
        embed = discord.Embed(
            title=f"🏆 {context.guild.name} Leaderboard",
            description="Top members by XP",
            color=0xBEBEFE,
        )

        # Add leaderboard entries
        leaderboard_text = ""
        for idx, (user_id, xp, level, messages) in enumerate(leaderboard, start=offset + 1):
            # Try to get member from cache first
            user = context.guild.get_member(user_id)

            # If not in cache, try to fetch from API
            if not user:
                try:
                    user = await context.guild.fetch_member(user_id)
                except discord.NotFound:
                    # Member left the server, try to get basic user info
                    try:
                        user = await self.bot.fetch_user(user_id)
                    except:
                        user = None
                except:
                    user = None

            # Get the display name or username
            if user:
                username = user.display_name if hasattr(user, 'display_name') else user.name
            else:
                username = f"User {user_id}"

            # Add medal emojis for top 3
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"**#{idx}**"

            leaderboard_text += f"{medal} **{username}**\n"
            leaderboard_text += f"└─ Level {level} • {xp:,} XP • {messages:,} messages\n\n"

        embed.description = leaderboard_text
        embed.set_footer(text=f"Page {page} • Use /leaderboard [page] to view other pages")

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="levelroles",
        description="List all level role rewards configured for this server.",
    )
    async def levelroles(self, context: Context) -> None:
        """
        Display all configured level role rewards.

        :param context: The application command context.
        """
        roles = await self.bot.database.get_level_roles(context.guild.id)

        if not roles:
            embed = discord.Embed(
                description="No level role rewards are configured yet!\nAdmins can use `/setlevelrole` to add rewards.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Create embed
        embed = discord.Embed(
            title="🎁 Level Role Rewards",
            description="Reach these levels to earn special roles!",
            color=0xBEBEFE,
        )

        # Add role rewards
        roles_text = ""
        for level, role_id in roles:
            role = context.guild.get_role(role_id)
            role_mention = role.mention if role else f"<Deleted Role {role_id}>"
            roles_text += f"**Level {level}** → {role_mention}\n"

        embed.description = roles_text
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="givexp",
        description="Give or remove XP from a user (Admin only).",
    )
    @app_commands.describe(
        user="The user to give/remove XP",
        amount="Amount of XP (use negative to remove)",
    )
    @commands.has_permissions(administrator=True)
    async def givexp(self, context: Context, user: discord.Member, amount: int) -> None:
        """
        Give or remove XP from a user.

        :param context: The application command context.
        :param user: The user to modify.
        :param amount: Amount of XP to add (negative to remove).
        """
        if user.bot:
            embed = discord.Embed(
                description="You cannot give XP to bots!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Get current data to show before/after
        old_data = await self.bot.database.get_user_level_data(user.id, context.guild.id)
        old_xp = old_data["xp"] if old_data else 0
        old_level = old_data["level"] if old_data else 0

        # Add XP
        from datetime import datetime

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_xp, new_level, _, leveled_up = await self.bot.database.add_xp(
            user.id, context.guild.id, amount, current_time
        )

        # Create response embed
        embed = discord.Embed(
            title="✅ XP Modified",
            color=0x2ECC71 if amount > 0 else 0xE02B2B,
        )
        embed.add_field(
            name="User",
            value=user.mention,
            inline=True,
        )
        embed.add_field(
            name="Change",
            value=f"{'+' if amount > 0 else ''}{amount:,} XP",
            inline=True,
        )
        embed.add_field(
            name="Result",
            value=f"{old_xp:,} → {new_xp:,} XP\nLevel {old_level} → {new_level}",
            inline=False,
        )

        await context.send(embed=embed)

        # Handle role rewards if leveled up
        if leveled_up and new_level > old_level:
            await self._assign_level_roles(user, new_level, context.guild)

    @commands.hybrid_command(
        name="setxp",
        description="Set a user's XP to a specific amount (Admin only).",
    )
    @app_commands.describe(
        user="The user to modify",
        amount="The exact XP amount to set",
    )
    @commands.has_permissions(administrator=True)
    async def setxp(self, context: Context, user: discord.Member, amount: int) -> None:
        """
        Set a user's XP to a specific amount.

        :param context: The application command context.
        :param user: The user to modify.
        :param amount: The XP amount to set.
        """
        if user.bot:
            embed = discord.Embed(
                description="You cannot modify bot XP!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        if amount < 0:
            embed = discord.Embed(
                description="XP amount must be non-negative!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Set XP
        new_xp, new_level = await self.bot.database.set_xp(
            user.id, context.guild.id, amount
        )

        # Create response embed
        embed = discord.Embed(
            title="✅ XP Set",
            description=f"Set {user.mention}'s XP to **{new_xp:,}** (Level **{new_level}**)",
            color=0x2ECC71,
        )

        await context.send(embed=embed)

        # Handle role rewards
        await self._assign_level_roles(user, new_level, context.guild)

    @commands.hybrid_command(
        name="resetxp",
        description="Reset a user's XP and level to 0 (Admin only).",
    )
    @app_commands.describe(user="The user to reset")
    @commands.has_permissions(administrator=True)
    async def resetxp(self, context: Context, user: discord.Member) -> None:
        """
        Reset a user's XP and level to 0.

        :param context: The application command context.
        :param user: The user to reset.
        """
        if user.bot:
            embed = discord.Embed(
                description="You cannot reset bot XP!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Reset XP
        success = await self.bot.database.reset_xp(user.id, context.guild.id)

        if not success:
            embed = discord.Embed(
                description=f"{user.mention} has no XP data to reset!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        embed = discord.Embed(
            title="✅ XP Reset",
            description=f"Reset {user.mention}'s XP and level to 0.",
            color=0x2ECC71,
        )

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="setlevelrole",
        description="Set a role reward for reaching a specific level (Admin only).",
    )
    @app_commands.describe(
        level="The level to assign the role at",
        role="The role to assign",
    )
    @commands.has_permissions(administrator=True)
    async def setlevelrole(
        self, context: Context, level: int, role: discord.Role
    ) -> None:
        """
        Configure a role to be assigned when users reach a specific level.

        :param context: The application command context.
        :param level: The level requirement.
        :param role: The role to assign.
        """
        if level < 1:
            embed = discord.Embed(
                description="Level must be 1 or higher!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        # Add role reward
        await self.bot.database.add_level_role(context.guild.id, level, role.id)

        embed = discord.Embed(
            title="✅ Level Role Set",
            description=f"Users who reach **Level {level}** will now receive {role.mention}!",
            color=0x2ECC71,
        )

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="removelevelrole",
        description="Remove a level role reward (Admin only).",
    )
    @app_commands.describe(level="The level to remove the role reward from")
    @commands.has_permissions(administrator=True)
    async def removelevelrole(self, context: Context, level: int) -> None:
        """
        Remove a role reward from a specific level.

        :param context: The application command context.
        :param level: The level to remove the reward from.
        """
        success = await self.bot.database.remove_level_role(context.guild.id, level)

        if not success:
            embed = discord.Embed(
                description=f"No role reward is configured for Level {level}!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        embed = discord.Embed(
            title="✅ Level Role Removed",
            description=f"Removed the role reward for **Level {level}**.",
            color=0x2ECC71,
        )

        await context.send(embed=embed)

    async def _assign_level_roles(
        self, user: discord.Member, level: int, guild: discord.Guild
    ) -> None:
        """
        Assign role rewards based on user's level.

        :param user: The user to assign roles to.
        :param level: The user's current level.
        :param guild: The guild to check for role rewards.
        """
        # Get all role rewards
        role_rewards = await self.bot.database.get_level_roles(guild.id)

        if not role_rewards:
            return

        # Find the highest role reward the user qualifies for
        highest_role_id = None
        highest_level = 0

        for reward_level, role_id in role_rewards:
            if reward_level <= level and reward_level > highest_level:
                highest_level = reward_level
                highest_role_id = role_id

        if highest_role_id is None:
            return

        # Get the role
        role = guild.get_role(highest_role_id)
        if role is None:
            return

        # Add role if user doesn't have it
        if role not in user.roles:
            try:
                await user.add_roles(role, reason=f"Reached Level {highest_level}")
                self.bot.logger.info(
                    f"Assigned role {role.name} to {user.name} for reaching Level {highest_level}"
                )
            except discord.Forbidden:
                self.bot.logger.warning(
                    f"Failed to assign role {role.name} to {user.name} - Missing permissions"
                )
            except Exception as e:
                self.bot.logger.error(
                    f"Error assigning role {role.name} to {user.name}: {e}"
                )


# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.
async def setup(bot) -> None:
    await bot.add_cog(Levels(bot))
