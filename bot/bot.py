import os
import asyncio
import discord
import aiosqlite
import wavelink
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class MyBot(commands.Bot):
    def __init__(self):
        # Configurar intents mínimos necesarios (seguridad)
        intents = discord.Intents.default()
        intents.members = True          # Para mensajes de bienvenida
        intents.message_content = True  # Para el sistema de niveles (XP)
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False

    async def setup_hook(self):
        """Inicialización de base de datos y carga de extensiones."""
        # Inicializar Base de Datos para Niveles
        async with aiosqlite.connect("levels.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT,
                    guild_id TEXT,
                    xp INTEGER,
                    level INTEGER,
                    last_xp TEXT,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            await db.commit()

        # Cargar los Cogs
        await self.load_extension("cogs.welcome")
        await self.load_extension("cogs.levels")
        await self.load_extension("cogs.moderation")
        await self.load_extension("cogs.music")
        print("Extensiones cargadas correctamente.")

        # Iniciar conexión a Lavalink en background de forma segura
        self.wavelink_task = asyncio.create_task(self._connect_lavalink())

    async def _connect_lavalink(self):
        """Maneja la conexión a Lavalink de forma segura con reintentos."""
        print("Intentando conectar con Lavalink...")
        while not hasattr(self, "wavelink_connected"):
            try:
                lava_host = os.getenv('LAVALINK_HOST', 'localhost')
                lava_port = os.getenv('LAVALINK_PORT', '2333')
                lava_pass = os.getenv('LAVALINK_PASSWORD')
                
                if not lava_pass:
                    print("❌ ERROR: No se encontró LAVALINK_PASSWORD. Configura la variable de entorno.")
                    return
                
                uri = f"http://{lava_host}:{lava_port}"
                
                nodes = [wavelink.Node(uri=uri, password=lava_pass)]
                await wavelink.Pool.connect(nodes=nodes, client=self)
                self.wavelink_connected = True
                print(f"✅ Lavalink conectado en {uri}")
            except Exception as e:
                print(f"❌ Reintentando conexión con Lavalink en 5s... ({e})")
                await asyncio.sleep(5)

    async def on_ready(self):
        # Sincronizar comandos globalmente
        if not self.synced:
            try:
                await self.tree.sync()
                self.synced = True
                print("Comandos sincronizados.")
            except Exception as e:
                print(f'Error al sincronizar comandos: {e}')
        
        print(f'Bot conectado como {self.user} (ID: {self.user.id})')
        print(f'Latencia actual: {round(self.latency * 1000)}ms')
        print('------')
        print('Bot listo y extensiones activas.')

# Instanciar el bot
bot = MyBot()

@bot.tree.command(name="ping", description="Responde con la latencia del bot")
async def ping(interaction: discord.Interaction):
    """Comando slash básico de ping."""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 ¡Pong! Latencia: {latency}ms")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Manejador global de errores para comandos slash."""
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ No tienes permisos suficientes para usar este comando.", ephemeral=True)
    else:
        print(f"Error no manejado en comando slash: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Ocurrió un error inesperado al ejecutar el comando.", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: No se encontró DISCORD_TOKEN.")
    else:
        bot.run(TOKEN)
