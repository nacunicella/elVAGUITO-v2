import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from datetime import datetime, timedelta

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "levels.db"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Sistema de XP: otorga 15 XP por mensaje con cooldown de 60 segundos."""
        if message.author.bot or not message.guild:
            return

        async with aiosqlite.connect(self.db_name) as db:
            # Buscar al usuario en la base de datos
            async with db.execute(
                "SELECT xp, level, last_xp FROM users WHERE user_id = ? AND guild_id = ?",
                (str(message.author.id), str(message.guild.id))
            ) as cursor:
                row = await cursor.fetchone()

            now = datetime.utcnow()
            
            if row:
                xp, level, last_xp_str = row
                last_xp = datetime.fromisoformat(last_xp_str)
                
                # Verificar cooldown de 60 segundos
                if now - last_xp < timedelta(seconds=60):
                    return

                new_xp = xp + 15
                # Fórmula de nivel: nivel = int((xp / 100) ** 0.5)
                new_level = int((new_xp / 100) ** 0.5)
                
                await db.execute(
                    "UPDATE users SET xp = ?, level = ?, last_xp = ? WHERE user_id = ? AND guild_id = ?",
                    (new_xp, new_level, now.isoformat(), str(message.author.id), str(message.guild.id))
                )
                await db.commit()

                # Notificar subida de nivel
                if new_level > level:
                    await message.channel.send(f"⬆️ {message.author.mention} subió al nivel {new_level}!")
            else:
                # Si el usuario no existe, crearlo
                await db.execute(
                    "INSERT INTO users (user_id, guild_id, xp, level, last_xp) VALUES (?, ?, ?, ?, ?)",
                    (str(message.author.id), str(message.guild.id), 15, 0, now.isoformat())
                )
                await db.commit()

    @app_commands.command(name="rank", description="Muestra tu nivel y XP actual")
    async def rank(self, interaction: discord.Interaction):
        """Comando slash para ver el rango individual."""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
                (str(interaction.user.id), str(interaction.guild.id))
            ) as cursor:
                row = await cursor.fetchone()
        
        if not row:
            await interaction.response.send_message("Aún no tienes XP registrada. ¡Escribe algo primero!", ephemeral=True)
            return

        xp, level = row
        next_level_xp = ((level + 1) ** 2) * 100
        
        embed = discord.Embed(title=f"Rango de {interaction.user.display_name}", color=0x3498db)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Nivel", value=str(level), inline=True)
        embed.add_field(name="XP Total", value=str(xp), inline=True)
        embed.add_field(name="Siguiente Nivel", value=f"{xp}/{next_level_xp} XP", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Muestra el Top 5 de usuarios del servidor")
    async def leaderboard(self, interaction: discord.Interaction):
        """Comando slash para ver el top 5 del servidor."""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT user_id, level, xp FROM users WHERE guild_id = ? ORDER BY xp DESC LIMIT 5",
                (str(interaction.guild.id),)
            ) as cursor:
                rows = await cursor.fetchall()
        
        embed = discord.Embed(title=f"🏆 Top 5 - {interaction.guild.name}", color=0xf1c40f)
        
        description = ""
        for i, (user_id, level, xp) in enumerate(rows, 1):
            user = interaction.guild.get_member(int(user_id))
            name = user.display_name if user else f"Usuario ID {user_id}"
            description += f"**{i}. {name}** - Nivel {level} ({xp} XP)\n"
        
        embed.description = description if description else "Nadie ha ganado XP todavía."
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Levels(bot))
