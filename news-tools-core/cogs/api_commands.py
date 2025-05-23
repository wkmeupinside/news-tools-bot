import disnake
from disnake.ext import commands, tasks

from api.main import start_server
from api.auth.auth_handler import sign_jwt
from config import DEV_GUILDS

from ext.models.checks import is_guild_admin
from ext.models.reusable import get_pending_embed


class API(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener(name="on_ready")
    async def on_ready(self):
        self.start_server.start()

    @commands.slash_command(
        name="apitoken",
        description="[DEV] Получить токен для API",
        guild_ids=DEV_GUILDS,
        dm_permission=False,
    )
    @commands.is_owner()
    @is_guild_admin()
    async def api_token(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            username: str = commands.Param(
                name="username", description="Имя пользователя токена"
            ),
    ):
        await interaction.response.send_message(embed=get_pending_embed(), ephemeral=True)

        token = await sign_jwt(username)

        return await interaction.edit_original_response(
            embed=None,
            content=f"JWT для пользователя **{username}**\n||```{token}```||\n*Храните токен в безопасном месте, никому его не передавайте.*\n*Токен подлежит замене через 30 дней.*"
        )

    @tasks.loop(count=1)
    async def start_server(self) -> None:
        await start_server(self.bot)


def setup(bot: commands.InteractionBot):
    bot.add_cog(API(bot))
