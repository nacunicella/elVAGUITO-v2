import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Envía un mensaje de bienvenida cuando un usuario se une al servidor."""
        # Buscar el canal llamado "bienvenida"
        channel = discord.utils.get(member.guild.text_channels, name="bienvenida")
        
        if channel:
            embed = discord.Embed(
                title=f"¡Bienvenido/a al servidor, {member.name}! 🎮",
                description=f"¡Hola {member.mention}! Esperamos que te diviertas mucho aquí.",
                color=0x3498db  # Azul
            )
            
            # Thumbnail con el avatar del usuario
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Campo con el número total de miembros
            embed.add_field(name="Miembros", value=f"{member.guild.member_count}", inline=False)
            
            # Footer con el nombre del servidor
            embed.set_footer(text=member.guild.name)
            
            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
