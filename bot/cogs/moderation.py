import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from datetime import datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "levels.db"

    async def cog_load(self):
        """Inicializar la tabla de advertencias al cargar el cog."""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    guild_id TEXT,
                    reason TEXT,
                    timestamp TEXT
                )
            """)
            await db.commit()

    async def log_action(self, guild, action, moderator, target, reason):
        """Enviar log al canal 'logs-moderación' si existe."""
        channel = discord.utils.get(guild.text_channels, name="logs-moderación")
        if channel:
            embed = discord.Embed(title=f"Log: {action}", color=0xff4757, timestamp=datetime.utcnow())
            embed.add_field(name="Usuario afectado", value=f"{target} ({target.id})", inline=False)
            embed.add_field(name="Moderador", value=f"{moderator} ({moderator.id})", inline=False)
            embed.add_field(name="Razón", value=reason, inline=False)
            await channel.send(embed=embed)

    @app_commands.command(name="kick", description="Expulsa a un usuario del servidor")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "No especificada"):
        """Expulsar a un usuario."""
        if usuario.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("No puedes kickear a alguien con un rango superior o igual al tuyo.", ephemeral=True)
        
        try:
            await usuario.kick(reason=razon)
            embed = discord.Embed(title="Usuario Expulsado", description=f"**{usuario}** ha sido expulsado.", color=0xff4757)
            embed.add_field(name="Razón", value=razon)
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "KICK", interaction.user, usuario, razon)
        except Exception as e:
            await interaction.response.send_message(f"Error al intentar expulsar: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="Banea a un usuario del servidor")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "No especificada"):
        """Banear a un usuario."""
        if usuario.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("No puedes banear a alguien con un rango superior o igual al tuyo.", ephemeral=True)

        try:
            await usuario.ban(reason=razon)
            embed = discord.Embed(title="Usuario Baneado", description=f"**{usuario}** ha sido baneado permanentemente.", color=0xff4757)
            embed.add_field(name="Razón", value=razon)
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "BAN", interaction.user, usuario, razon)
        except Exception as e:
            await interaction.response.send_message(f"Error al intentar banear: {e}", ephemeral=True)

    @app_commands.command(name="unban", description="Desbanea a un usuario (por su ID)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, razon: str = "No especificada"):
        """Desbanear a un usuario usando su ID."""
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=razon)
            embed = discord.Embed(title="Usuario Desbaneado", description=f"**{user}** ha sido desbaneado.", color=0x2ecc71)
            embed.add_field(name="Razón", value=razon)
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "UNBAN", interaction.user, user, razon)
        except discord.NotFound:
            await interaction.response.send_message("❌ Usuario no encontrado o no está baneado.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al intentar desbanear: {e}", ephemeral=True)

    @app_commands.command(name="warn", description="Añade una advertencia a un usuario")
    @app_commands.checks.has_permissions(kick_members=True)
    async def warn(self, interaction: discord.Interaction, usuario: discord.Member, razon: str):
        """Añadir advertencia y auto-kick si llega a 3."""
        async with aiosqlite.connect(self.db_name) as db:
            # Guardar la advertencia
            await db.execute(
                "INSERT INTO warnings (user_id, guild_id, reason, timestamp) VALUES (?, ?, ?, ?)",
                (str(usuario.id), str(interaction.guild.id), razon, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
            )
            await db.commit()

            # Contar cuántas tiene
            async with db.execute(
                "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND guild_id = ?",
                (str(usuario.id), str(interaction.guild.id))
            ) as cursor:
                count = (await cursor.fetchone())[0]

        embed = discord.Embed(title="Advertencia Añadida", color=0xeccc68)
        embed.add_field(name="Usuario", value=str(usuario), inline=True)
        embed.add_field(name="Advertencias totales", value=str(count), inline=True)
        embed.add_field(name="Razón", value=razon, inline=False)
        
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, "WARN", interaction.user, usuario, razon)

        # Auto-kick a las 3 advertencias
        if count >= 3:
            try:
                await usuario.kick(reason="Acumulación de 3 advertencias")
                await self.log_action(interaction.guild, "AUTO-KICK (3 WARNS)", self.bot.user, usuario, "3 Advertencias acumuladas")
                await interaction.channel.send(f"⚠️ **{usuario}** ha sido expulsado automáticamente por acumular 3 advertencias.")
            except Exception as e:
                print(f"Error al auto-kickear usuario (posible falta de permisos): {e}")

    @app_commands.command(name="warns", description="Ver el historial de advertencias de un usuario")
    async def warns(self, interaction: discord.Interaction, usuario: discord.Member):
        """Mostrar lista de advertencias."""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT reason, timestamp FROM warnings WHERE user_id = ? AND guild_id = ?",
                (str(usuario.id), str(interaction.guild.id))
            ) as cursor:
                rows = await cursor.fetchall()

        embed = discord.Embed(title=f"Historial de Warns: {usuario.display_name}", color=0xeccc68)
        embed.set_thumbnail(url=usuario.display_avatar.url)
        
        if not rows:
            embed.description = "Este usuario no tiene advertencias."
        else:
            embed.add_field(name="Total", value=str(len(rows)), inline=False)
            warn_list = ""
            for i, (reason, time) in enumerate(rows, 1):
                warn_list += f"**{i}.** [{time}] {reason}\n"
            embed.description = warn_list

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clearwarns", description="Borra todas las advertencias de un usuario")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearwarns(self, interaction: discord.Interaction, usuario: discord.Member):
        """Eliminar todo el historial de advertencias."""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("DELETE FROM warnings WHERE user_id = ? AND guild_id = ?", (str(usuario.id), str(interaction.guild.id)))
            await db.commit()

        await interaction.response.send_message(f"✅ Se han borrado todas las advertencias de **{usuario}**.")
        await self.log_action(interaction.guild, "CLEAR-WARNS", interaction.user, usuario, "Historial limpiado")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
