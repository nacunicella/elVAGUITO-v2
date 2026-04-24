import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
import datetime
import logging

# MONKEY PATCH: Solución definitiva al error 'channelId is required' en Lavalink 4.2+
# Wavelink 3.4.1 tiene un bug donde no envía el 'channelId' en el objeto 'voice'
# TODO: Eliminar este monkey-patch cuando se actualice a una versión de Wavelink 
# que solucione el bug de envío de 'channelId' requerido por Lavalink 4.2+
original_dispatch = wavelink.Player._dispatch_voice_update

async def patched_dispatch_voice_update(self):
    assert self.guild is not None
    data = self._voice_state["voice"]

    session_id = data.get("session_id", None)
    token = data.get("token", None)
    endpoint = data.get("endpoint", None)

    if not session_id or not token or not endpoint:
        return

    # AÑADIMOS EL CHANNELID QUE LAVALINK 4 ESTÁ EXIGIENDO
    channel_id = str(self.channel.id) if self.channel else ""
    request = {"voice": {
        "sessionId": session_id, 
        "token": token, 
        "endpoint": endpoint, 
        "channelId": channel_id
    }}

    try:
        await self.node._update_player(self.guild.id, data=request)
    except Exception as e:
        logging.error(f"Error en el monkey-patch de voice_update: {e}")
        await self.disconnect()
    else:
        self._connection_event.set()

# Aplicar el parche
wavelink.Player._dispatch_voice_update = patched_dispatch_voice_update

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        print(f"Empezo a sonar la pista: {payload.track.title}")

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        print(f"Error en Lavalink al reproducir la pista: {payload.exception}")

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload):
        print(f"La pista se ha quedado atascada: {payload.track.title}")

    @app_commands.command(name="play", description="Reproduce música")
    async def play(self, interaction: discord.Interaction, busqueda: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("❌ ¡Debes estar en un canal de voz!")

        player: wavelink.Player = interaction.guild.voice_client
        
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
            except Exception as e:
                return await interaction.followup.send(f"❌ Error de conexión: {e}")

        # Breve espera para que Discord registre el estado de voz (patch de Lavalink)
        await asyncio.sleep(1)

        try:
            # Buscar la pista en YouTube a través del nodo de Lavalink

            tracks = await wavelink.Playable.search(busqueda, source=wavelink.TrackSource.YouTube)
            
            if not tracks:
                return await interaction.followup.send("❌ No se encontraron resultados para tu búsqueda.")

            track = tracks[0]
            
            await player.play(track)
            
            embed = discord.Embed(
                title="🎶 Reproduciendo Ahora",
                description=f"**[{track.title}]({track.uri})**\n👤 Autor: `{track.author}`",
                color=0x2ecc71
            )
            
            # Si la pista tiene miniatura/carátula, la agregamos
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
                
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error al reproducir: {e}")

    @app_commands.command(name="stop", description="Detiene el bot")
    async def stop(self, interaction: discord.Interaction):
        player: wavelink.Player = interaction.guild.voice_client
        if player:
            await player.stop()
            await player.disconnect()
            await interaction.response.send_message("👋 Desconectado y música detenida.")

async def setup(bot):
    await bot.add_cog(Music(bot))
