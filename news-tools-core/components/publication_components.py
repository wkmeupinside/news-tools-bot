import datetime
from typing import Literal

import disnake
from disnake import ui, ModalInteraction, MessageInteraction

from database.methods import (
    publication_actions as action_methods,
    makers as maker_methods,
    guilds as guild_methods,
    publications as publication_methods,
)
from ext.tools import validate_date, get_status_title
from ext.profile_getters import get_publication_profile
from ext.models.reusable import *


class PublicationListPaginator(ui.View):
    def __init__(self, embeds: list[disnake.Embed]):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.current_page = 0

        embed: disnake.Embed
        for i, embed in enumerate(self.embeds):
            embed.set_footer(text=f"Страница {i + 1} из {len(embeds)}")

        self._update_state()

    @classmethod
    async def create(cls, guild_id: int):
        publications = await publication_methods.get_all_publications(guild_id=guild_id)
        guild = await guild_methods.get_guild_by_id(id=guild_id)

        if len(publications) == 0:
            embed = disnake.Embed(
                title=f"🧾 Выпуски новостного раздела {guild.guild_name}",
                colour=0x2B2D31,
                description="На сервере нет выпусков. Создайте один и вы сможете увидеть его здесь. ||А можете создать сразу много :)||.",
            )

            return None, embed

        next_embed_iteration = 10
        embeds = []
        for i in range(len(publications)):
            if publications[i].maker_id:
                maker = await maker_methods.get_maker_by_id(id=publications[i].maker_id)
                maker = maker.nickname
            else:
                maker = "Не установлен"

            status = get_status_title(status_kw=str(publications[i].status))

            if publications[i].date:
                date = publications[i].date.strftime("%d.%m.%Y")
            else:
                date = "Не указана"

            if i == 0:
                new_embed = disnake.Embed(
                    title=f"🧾 Выпуски новостного раздела {guild.guild_name}",
                    colour=0x2B2D31,
                    description=f"**ID | Номер выпуска | Никнейм редактора | Статус | Дата публикации**\n\n"
                                f"- **[ID: {publications[i].id}] | #{publications[i].publication_number} | {maker} | {status} | {date}**\n",
                )
                embeds.append(new_embed)
                continue

            if i == next_embed_iteration:
                new_embed = disnake.Embed(
                    title=f"🧾 Выпуски новостного раздела {guild.guild_name}",
                    colour=0x2B2D31,
                    description=f"**ID | Номер выпуска | Никнейм редактора | Статус | Дата публикации**\n\n"
                                f"- **[ID: {publications[i].id}] | #{publications[i].publication_number} | {maker} | {status} | {date}**\n",
                )
                embeds.append(new_embed)
                next_embed_iteration += 10
                continue

            embeds[
                -1
            ].description += f"- **[ID: {publications[i].id}] | #{publications[i].publication_number} | {maker} | {status} | {date}**\n"  # @formatter:off

        return cls(embeds=embeds), embeds[0]

    def _update_state(self) -> None:
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.embeds) - 1

    @disnake.ui.button(emoji="◀", style=disnake.ButtonStyle.secondary)
    async def prev_page(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.current_page -= 1
        self._update_state()

        await inter.response.edit_message(
            embed=self.embeds[self.current_page], view=self
        )

    @disnake.ui.button(emoji="▶", style=disnake.ButtonStyle.secondary)
    async def next_page(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.current_page += 1
        self._update_state()

        await inter.response.edit_message(
            embed=self.embeds[self.current_page], view=self
        )


class GearButton(ui.View):
    def __init__(self, author: disnake.Member, publication_id: int):
        super().__init__(timeout=120)
        self.author = author
        self.publication_id = publication_id

    @ui.button(emoji="<:service_gear:1207389592815407137>")
    async def open_editor(
        self, button: ui.Button, interaction: disnake.MessageInteraction
    ):
        if not interaction.author == self.author:
            return await interaction.send(
                content="**Вы не можете взаимодействовать с компонентом, который был вызван не вами.**",
                ephemeral=True,
            )

        main_menu = MainMenu(author=self.author, publication_id=self.publication_id)

        return await interaction.response.edit_message(view=main_menu)


class MainMenu(ui.View):
    def __init__(self, author: disnake.Member, publication_id: int):
        super().__init__(timeout=120)
        self.author = author
        self.publication_id = publication_id

    @ui.string_select(
        placeholder="🧾 | Выберите опцию из списка",
        row=1,
        options=[
            disnake.SelectOption(
                label="Изменить номер выпуска",
                value="number",
                emoji="<:hashtag:1220792495047184515>",
            ),
            disnake.SelectOption(
                label="Изменить редактора выпуска",
                value="maker",
                emoji="<:user:1220792994328875058>",
            ),
            disnake.SelectOption(
                label="Изменить дату выпуска",
                value="date",
                emoji="<:yellow_calendar:1207339611911884902>",
            ),
            disnake.SelectOption(
                label="Изменить статус выпуска",
                value="status",
                emoji="<:workinprogress:1220793552234086451>",
            ),
            disnake.SelectOption(
                label="Изменить зарплату за выпуск",
                value="salary",
                emoji="<:money:1220793737391771829>",
            ),
            disnake.SelectOption(
                label="Изменить автора информации",
                value="info_creator",
                emoji="<:user:1220792994328875058>",
            ),
            disnake.SelectOption(
                label="Изменить человека, выплатившего зарплату",
                value="salary_payer",
                emoji="<:user:1220792994328875058>",
            ),
            disnake.SelectOption(
                label="Удалить выпуск [3 LVL]",
                value="delete_publication",
                emoji="<:warn_sign:1207315803893145610>",
            ),
        ],
    )
    async def option_select_callback(
        self, string_select: ui.StringSelect, interaction: disnake.MessageInteraction
    ):
        if not interaction.author == self.author:
            return await interaction.send(
                content="**Вы не можете взаимодействовать с компонентом, который был вызван не вами.**",
                ephemeral=True,
            )

        selected_item = interaction.values[0]

        view = MainMenu(author=self.author, publication_id=self.publication_id)

        match selected_item:
            case "number":
                modal = SubmitText.create(
                    modal_type="number",
                    author=self.author,
                    publication_id=self.publication_id,
                )
                return await interaction.response.send_modal(modal=modal)
            case "maker":
                view = await ChooseMaker.create(
                    author=self.author,
                    publication_id=self.publication_id,
                    choose_type="maker",
                )
                return await interaction.response.edit_message(view=view)
            case "date":
                modal = SubmitText.create(
                    modal_type="date",
                    author=self.author,
                    publication_id=self.publication_id,
                )
                return await interaction.response.send_modal(modal=modal)
            case "status":
                view = SetStatus(author=self.author, publication_id=self.publication_id)
                return await interaction.response.edit_message(view=view)
            case "salary":
                modal = SubmitText.create(
                    modal_type="salary",
                    author=self.author,
                    publication_id=self.publication_id,
                )
                return await interaction.response.send_modal(modal=modal)
            case "info_creator":
                view = await ChooseMaker.create(
                    author=self.author,
                    publication_id=self.publication_id,
                    choose_type="info_creator",
                )
                return await interaction.response.edit_message(view=view)
            case "salary_payer":
                view = await ChooseMaker.create(
                    author=self.author,
                    publication_id=self.publication_id,
                    choose_type="salary_payer",
                )
                return await interaction.response.edit_message(view=view)
            case "delete_publication":
                await interaction.response.send_message(embed=get_pending_embed())

                guild = await guild_methods.get_guild(discord_id=interaction.guild.id)

                interaction_author = await maker_methods.get_maker(
                    guild_id=guild.id, discord_id=interaction.author.id
                )

                if not interaction_author:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif not interaction_author.account_status:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif int(interaction_author.level) < 3:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                publication = await publication_methods.get_publication_by_id(
                    id=self.publication_id
                )

                if not publication:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                elif not publication.guild_id == interaction_author.guild_id:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                await publication_methods.delete_publication_by_id(
                    publication_id=publication.id
                )

                await action_methods.add_pub_action(
                    pub_id=publication.id,
                    made_by=interaction_author.id,
                    action="deletepub",
                    meta=publication.id,
                )

                await interaction.edit_original_response(
                    embed=get_success_embed(f"Вы удалили выпуск **#{publication.publication_number}**.")
                )

                return await interaction.message.delete()

    @ui.button(label="Отмена", style=disnake.ButtonStyle.red, row=2)
    async def cancel_callback(
        self, button: ui.Button, interaction: disnake.MessageInteraction
    ):
        if not interaction.author == self.author:
            return await interaction.send(
                content="**Вы не можете взаимодействовать с компонентом, который был вызван не вами.**",
                ephemeral=True,
            )

        return await interaction.response.edit_message(
            view=GearButton(author=self.author, publication_id=self.publication_id)
        )


class BackToMenu(ui.Button):
    def __init__(self, row: int, author: disnake.Member, publication_id: int):
        super().__init__(style=disnake.ButtonStyle.blurple, label="Назад", row=row)

        self.author = author
        self.publication_id = publication_id

    async def callback(self, interaction: disnake.MessageInteraction, /) -> None:
        if not interaction.author == self.author:
            return await interaction.send(
                content="**Вы не можете взаимодействовать с компонентом, который был вызван не вами.**",
                ephemeral=True,
            )

        main_menu = MainMenu(author=self.author, publication_id=self.publication_id)
        return await interaction.response.edit_message(view=main_menu)


class SubmitText(ui.Modal):
    def __init__(
        self,
        modal_title: str,
        modal_type: Literal["number", "date", "salary"],
        components,
        author: disnake.Member,
        publication_id: int,
    ):
        super().__init__(title=modal_title, components=components, timeout=120)
        self.modal_type = modal_type
        self.author = author
        self.publication_id = publication_id

    @classmethod
    def create(
        cls,
        modal_type: Literal["number", "date", "salary"],
        author: disnake.Member,
        publication_id: int,
    ):
        match modal_type:
            case "number":
                self = cls(
                    modal_title="Укажите новый номер для выпуска",
                    modal_type=modal_type,
                    author=author,
                    publication_id=publication_id,
                    components=ui.TextInput(
                        label="Номер выпуска",
                        custom_id="publication_number",
                        placeholder="Укажите число",
                        max_length=5,
                    ),
                )

            case "date":
                self = cls(
                    modal_title="Укажите дату",
                    modal_type=modal_type,
                    author=author,
                    publication_id=publication_id,
                    components=ui.TextInput(
                        label="Дата (оставьте пустым чтобы очистить дату)",
                        custom_id="date",
                        placeholder="Укажите дату в формате ГГГГ-ММ-ДД",
                        required=False,
                        min_length=10,
                        max_length=10,
                    ),
                )

            case "salary" | _:
                self = cls(
                    modal_title="Укажите зарплату за выпуск",
                    modal_type=modal_type,
                    author=author,
                    publication_id=publication_id,
                    components=ui.TextInput(
                        label="Зарплата за выпуск",
                        custom_id="salary",
                        placeholder="Укажите число (оставьте пустым чтобы очистить зарплату)",
                        required=False,
                        max_length=8,
                    ),
                )

        return self

    async def callback(self, interaction: ModalInteraction, /):
        if not interaction.author == self.author:
            return await interaction.send(
                content="**Вы не можете взаимодействовать с компонентом, который был вызван не вами.**",
                ephemeral=True,
            )

        view = MainMenu(author=self.author, publication_id=self.publication_id)

        match self.modal_type:
            case "number":
                await interaction.response.send_message(embed=get_pending_embed())

                guild = await guild_methods.get_guild(discord_id=interaction.guild.id)

                interaction_author = await maker_methods.get_maker(
                    guild_id=guild.id, discord_id=interaction.author.id
                )

                publication = await publication_methods.get_publication_by_id(
                    id=self.publication_id
                )

                try:
                    new_number = int(interaction.text_values.get("publication_number"))
                except ValueError:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed(f"Номер указан неверно. В качестве номера может быть указано только число. Вы указали **«{interaction.text_values.get('publication_number')}»**.")
                    )

                if not interaction_author:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif not interaction_author.account_status:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif int(interaction_author.level) < 2:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                if not publication:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                elif not publication.guild_id == interaction_author.guild_id:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                elif publication.publication_number == new_number:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed(f"Выпуску уже присвоен номер **#{new_number}**.")
                    )

                _new_publication = await publication_methods.get_publication(
                    guild_id=guild.id, publication_number=new_number
                )

                if _new_publication:
                    await interaction.message.edit(view=view)

                    embed = await get_publication_profile(publication_id=new_number)
                    return await interaction.edit_original_response(
                        embeds=[get_failed_embed(f"Номер **#{new_number}** занят другим выпуском."), embed],
                        view=GearButton(
                            author=self.author, publication_id=_new_publication.id
                        ),
                    )

                await publication_methods.update_publication_by_id(
                    publication_id=publication.id,
                    column_name="publication_number",
                    value=new_number,
                )

                await action_methods.add_pub_action(
                    pub_id=publication.id,
                    made_by=interaction_author.id,
                    action="setpub_id",
                    meta=f"[{publication.publication_number}, {new_number}]",
                )

                embed = await get_publication_profile(
                    publication_id=self.publication_id
                )

                await interaction.message.edit(embed=embed, view=view)

                return await interaction.edit_original_response(
                    embed=get_success_embed(f"Вы изменили номер выпуска с **#{publication.publication_number}** на **#{new_number}**.")
                )

            case "date":
                await interaction.response.send_message(embed=get_pending_embed())

                guild = await guild_methods.get_guild(discord_id=interaction.guild.id)

                interaction_author = await maker_methods.get_maker(
                    guild_id=guild.id, discord_id=interaction.author.id
                )

                if not interaction_author:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif not interaction_author.account_status:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif int(interaction_author.level) < 2:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                date = interaction.text_values.get("date")
                if date == "":
                    date = None

                if date:
                    is_date_valid = validate_date(date)

                    if not is_date_valid:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed("Дата указана неверно. Укажите дату в формате `ГГГГ-ММ-ДД`.")
                        )

                publication = await publication_methods.get_publication_by_id(
                    id=self.publication_id
                )

                if not publication:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                elif not publication.guild_id == interaction_author.guild_id:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                if date:
                    if publication.date == datetime.date.fromisoformat(date):
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"Дата **{date}** уже установлена для выпуска **#{publication.publication_number}**.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id, column_name="date", value=date
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_date",
                        meta=date,
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы изменили дату публикации выпуска **#{publication.publication_number}** на **{date}**.")
                    )
                else:
                    if not publication.date:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"Дата публикации выпуска **#{publication.publication_number}** не установлена.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="date",
                        value=None,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_date",
                        meta="не указана",
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы очистили дату публикации выпуска **#{publication.publication_number}**.")
                    )

                embed = await get_publication_profile(
                    publication_id=self.publication_id
                )

                return await interaction.message.edit(embed=embed, view=view)

            case "salary":
                await interaction.response.send_message(embed=get_pending_embed())

                guild = await guild_methods.get_guild(discord_id=interaction.guild.id)

                interaction_author = await maker_methods.get_maker(
                    guild_id=guild.id, discord_id=interaction.author.id
                )

                if not interaction_author:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif not interaction_author.account_status:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif int(interaction_author.level) < 2:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                publication = await publication_methods.get_publication_by_id(
                    id=self.publication_id
                )

                if not publication:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                elif not publication.guild_id == interaction_author.guild_id:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                salary = interaction.text_values.get("salary")
                if salary == "":
                    salary = None
                else:
                    try:
                        salary = int(salary)
                    except ValueError:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"Неверно указана зарплата выпуска. Значение может быть только числом. Вы указали **«{interaction.text_values.get('salary')}»**.")
                        )

                if salary:
                    if publication.amount_dp == salary:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"За выпуск **#{publication.publication_number}** уже установлена зарплата **{salary}**.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="amount_dp",
                        value=salary,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_amount",
                        meta=salary,
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы установили зарплату за выпуск **#{publication.publication_number}** на **{salary}**.")
                    )
                else:
                    if not publication.amount_dp:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"Зарплата за выпуск **#{publication.publication_number}** не установлена.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="amount_dp",
                        value=None,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_amount",
                        meta="не установлено",
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы очистили зарплату за выпуск **#{publication.publication_number}**.")
                    )

                embed = await get_publication_profile(
                    publication_id=self.publication_id
                )

                return await interaction.message.edit(embed=embed, view=view)

            case _:
                return


class ChooseMaker(ui.View):
    def __init__(
        self,
        author: disnake.Member,
        publication_id: int,
        choose_type: Literal["maker", "info_creator", "salary_payer"],
        options_list: list[list[disnake.SelectOption]],
    ):
        super().__init__(timeout=120)
        self.author = author
        self.publication_id = publication_id

        self.add_item(BackToMenu(row=4, author=author, publication_id=publication_id))

        self.page_index = 0
        self.options_list = options_list

        self.select_maker = SelectMaker(
            author=author,
            publication_id=publication_id,
            options=self.options_list[0],
            choose_type=choose_type,
        )
        self.select_maker.placeholder = f"🧾 | Выберите редактора из списка ({self.page_index + 1}/{len(self.options_list)})"

        self.add_item(self.select_maker)
        self._update_state()

        match choose_type:
            case "maker":
                action_type = ui.StringSelect(
                    options=[
                        disnake.SelectOption(
                            label="Изменить редактора выпуска",
                            value="maker",
                            emoji="<:user:1220792994328875058>",
                            default=True,
                        )
                    ],
                    disabled=True,
                    row=1,
                )
            case "info_creator":
                action_type = ui.StringSelect(
                    options=[
                        disnake.SelectOption(
                            label="Изменить автора информации",
                            value="info_creator",
                            emoji="<:user:1220792994328875058>",
                            default=True,
                        )
                    ],
                    disabled=True,
                    row=1,
                )
            case "salary_payer" | _:
                action_type = ui.StringSelect(
                    options=[
                        disnake.SelectOption(
                            label="Изменить человека, выплатившего зарплату",
                            value="salary_payer",
                            emoji="<:user:1220792994328875058>",
                            default=True,
                        )
                    ],
                    disabled=True,
                    row=1,
                )

        self.add_item(action_type)

    def _update_state(self):
        self.previous_page.disabled = self.page_index == 0
        self.next_page.disabled = self.page_index == len(self.options_list) - 1

    @ui.button(emoji="◀", style=disnake.ButtonStyle.secondary, row=3)
    async def previous_page(
        self, button: ui.Button, interaction: disnake.MessageInteraction
    ):
        self.page_index -= 1
        self._update_state()

        self.select_maker.placeholder = f"🧾 | Выберите редактора из списка ({self.page_index + 1}/{len(self.options_list)})"
        self.select_maker.options = self.options_list[self.page_index]

        return await interaction.response.edit_message(view=self)

    @ui.button(emoji="▶", style=disnake.ButtonStyle.secondary, row=3)
    async def next_page(
        self, button: ui.Button, interaction: disnake.MessageInteraction
    ):
        self.page_index += 1
        self._update_state()

        self.select_maker.placeholder = f"🧾 | Выберите редактора из списка ({self.page_index + 1}/{len(self.options_list)})"
        self.select_maker.options = self.options_list[self.page_index]

        return await interaction.response.edit_message(view=self)

    @classmethod
    async def create(
        cls,
        author: disnake.Member,
        publication_id: int,
        choose_type: Literal["maker", "info_creator", "salary_payer"],
    ):
        guild = await guild_methods.get_guild(discord_id=author.guild.id)
        makers = await maker_methods.get_all_makers_sorted_by_lvl(guild_id=guild.id)

        options_list = []

        iteration = 2
        total_iterations = 1

        _current_list = [
            disnake.SelectOption(
                label="Очистить поле",
                value="-1",
                emoji="⛔",
                description="Чтобы очистить поле выберите этот вариант",
            )
        ]

        for maker in makers:
            _current_list.append(
                disnake.SelectOption(
                    label=maker.nickname,
                    value=str(maker.id),
                    emoji=(
                        "<:user:1220792994328875058>"
                        if maker.account_status
                        else "<:user_red:1223319477308100641>"
                    ),
                )
            )

            if (iteration == 25) or (total_iterations == len(makers)):
                options_list.append(_current_list.copy())
                _current_list.clear()
                iteration = 1
                total_iterations += 1
                continue

            iteration += 1
            total_iterations += 1

        self = cls(
            author=author,
            publication_id=publication_id,
            choose_type=choose_type,
            options_list=options_list,
        )

        return self


class SelectMaker(ui.StringSelect):
    def __init__(
        self,
        author: disnake.Member,
        publication_id: int,
        options: list[disnake.SelectOption],
        choose_type: Literal["maker", "info_creator", "salary_payer"],
    ):
        super().__init__(
            placeholder="🧾 | Выберите редактора из списка", row=2, options=options
        )
        self.author = author
        self.publication_id = publication_id
        self.choose_type = choose_type

    async def callback(self, interaction: MessageInteraction, /):
        if not interaction.author == self.author:
            return await interaction.send(
                content="**Вы не можете взаимодействовать с компонентом, который был вызван не вами.**",
                ephemeral=True,
            )

        maker_id = int(interaction.values[0])
        if maker_id == -1:
            maker_id = None

        view = await ChooseMaker.create(
            author=self.author,
            publication_id=self.publication_id,
            choose_type=self.choose_type,
        )

        match self.choose_type:
            case "maker":
                await interaction.response.send_message(embed=get_pending_embed())

                guild = await guild_methods.get_guild(discord_id=interaction.guild.id)

                interaction_author = await maker_methods.get_maker(
                    guild_id=guild.id, discord_id=interaction.author.id
                )

                if not interaction_author:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif not interaction_author.account_status:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif int(interaction_author.level) < 2:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                publication = await publication_methods.get_publication_by_id(
                    id=self.publication_id
                )

                if not publication:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                elif not publication.guild_id == interaction_author.guild_id:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                if maker_id:
                    maker = await maker_methods.get_maker_by_id(id=maker_id)

                    if not maker:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed("Выбранный вами пользователь не зарегистрирован в системе.")
                        )

                    if publication.maker_id == maker.id:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_success_embed(f"Для выпуска **#{publication.publication_number}** уже установлен редактор **{maker.nickname}**.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="maker_id",
                        value=maker.id,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_maker",
                        meta=maker.id,
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы установили редактора выпуска **#{publication.publication_number}** на **{maker.nickname}**.")
                    )

                else:
                    if not publication.maker_id:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"У выпуска **#{publication.publication_number}** не установлен редактор.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="maker_id",
                        value=None,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_maker",
                        meta="не указан",
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы очистили редактора выпуска **#{publication.publication_number}**.")
                    )

                embed = await get_publication_profile(publication_id=publication.id)

                return await interaction.message.edit(embed=embed, view=view)

            case "info_creator":
                await interaction.response.send_message(embed=get_pending_embed())

                guild = await guild_methods.get_guild(discord_id=interaction.guild.id)

                interaction_author = await maker_methods.get_maker(
                    guild_id=guild.id, discord_id=interaction.author.id
                )

                if not interaction_author:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif not interaction_author.account_status:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif int(interaction_author.level) < 2:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                publication = await publication_methods.get_publication_by_id(
                    id=self.publication_id
                )

                if not publication:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                elif not publication.guild_id == interaction_author.guild_id:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                if maker_id:
                    creator = await maker_methods.get_maker_by_id(id=maker_id)

                    if not creator:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed("Выбранный вами пользователь не зарегистрирован в системе.")
                        )

                    if publication.information_creator_id == creator.id:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"Для выпуска **#{publication.publication_number}** уже установлен автор информации **{creator.nickname}**.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="information_creator_id",
                        value=creator.id,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_infocreator",
                        meta=creator.id,
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы установили автора информации к выпуску **#{publication.publication_number}** на **{creator.nickname}**.")
                    )

                else:
                    if not publication.information_creator_id:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"Для выпуска **#{publication.publication_number}** автор информации не установлен.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="information_creator_id",
                        value=None,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_infocreator",
                        meta="не указан",
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы очистили автора информации к выпуску **#{publication.publication_number}**.")
                    )

                embed = await get_publication_profile(publication_id=publication.id)

                return await interaction.message.edit(embed=embed, view=view)

            case "salary_payer":
                await interaction.response.send_message(embed=get_pending_embed())

                guild = await guild_methods.get_guild(discord_id=interaction.guild.id)

                interaction_author = await maker_methods.get_maker(
                    guild_id=guild.id, discord_id=interaction.author.id
                )

                if not interaction_author:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif not interaction_author.account_status:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                elif int(interaction_author.level) < 2:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
                    )

                publication = await publication_methods.get_publication_by_id(
                    id=self.publication_id
                )

                if not publication:
                    await interaction.message.edit(view=view)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                elif not publication.guild_id == interaction_author.guild_id:
                    await interaction.message.edit(view=None)

                    return await interaction.edit_original_response(
                        embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
                    )

                if maker_id:
                    salary_payer = await maker_methods.get_maker_by_id(id=maker_id)

                    if publication.salary_payer_id == salary_payer.id:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"Выплативший зарплату за выпуск **#{publication.publication_number}** человек не установлен.")
                        )

                    if not salary_payer:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed("Выбранный вами пользователь не зарегистрирован в системе.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="salary_payer_id",
                        value=salary_payer.id,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_salarypayer",
                        meta=salary_payer.id,
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы установили выплатившего зарплату человека за выпуск **#{publication.publication_number}** на **{salary_payer.nickname}**.")
                    )

                else:
                    if not publication.salary_payer_id:
                        await interaction.message.edit(view=view)

                        return await interaction.edit_original_response(
                            embed=get_failed_embed(f"Выплативший зарплату человек за выпуск **#{publication.publication_number}** не установлен.")
                        )

                    await publication_methods.update_publication_by_id(
                        publication_id=publication.id,
                        column_name="salary_payer_id",
                        value=None,
                    )

                    await action_methods.add_pub_action(
                        pub_id=publication.id,
                        made_by=interaction_author.id,
                        action="setpub_salarypayer",
                        meta="не указан",
                    )

                    await interaction.edit_original_response(
                        embed=get_success_embed(f"Вы очистили выплатившего зарплату человека за выпуск **#{publication.publication_number}**.")
                    )

                embed = await get_publication_profile(publication_id=publication.id)

                return await interaction.message.edit(embed=embed, view=view)


class SetStatus(ui.View):
    def __init__(self, author: disnake.Member, publication_id: int):
        super().__init__(timeout=120)
        self.author = author
        self.publication_id = publication_id

        self.add_item(
            ui.StringSelect(
                disabled=True,
                row=1,
                options=[
                    disnake.SelectOption(
                        label="Изменить статус выпуска",
                        value="status",
                        emoji="<:workinprogress:1220793552234086451>",
                        default=True,
                    )
                ],
            )
        )

        self.add_item(BackToMenu(row=3, author=author, publication_id=publication_id))

    @ui.string_select(
        placeholder="🧾 | Выберите статус",
        row=2,
        options=[
            disnake.SelectOption(
                label="Сделан",
                value="completed",
                emoji="<:completed:1223369737245822987>",
            ),
            disnake.SelectOption(
                label="В процессе",
                value="in_process",
                emoji="<:in_process:1223369491430506647>",
            ),
            disnake.SelectOption(
                label="Провален", value="failed", emoji="<:failed:1223369646980206704>"
            ),
        ],
    )
    async def select_status(
        self, string_select: ui.StringSelect, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_message(embed=get_pending_embed())

        guild = await guild_methods.get_guild(discord_id=interaction.guild.id)

        interaction_author = await maker_methods.get_maker(
            guild_id=guild.id, discord_id=interaction.author.id
        )

        if not interaction_author:
            await interaction.message.edit(view=self)

            return await interaction.edit_original_response(
                embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
            )

        elif not interaction_author.account_status:
            await interaction.message.edit(view=self)

            return await interaction.edit_original_response(
                embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
            )

        elif int(interaction_author.level) < 2:
            await interaction.message.edit(view=self)

            return await interaction.edit_original_response(
                embed=get_failed_embed("У вас недостаточно прав для выполнения данного взаимодействия.")
            )

        publication = await publication_methods.get_publication_by_id(
            id=self.publication_id
        )

        status = interaction.values[0]

        status_title = get_status_title(status)

        if not publication:
            await interaction.message.edit(view=None)

            return await interaction.edit_original_response(
                embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
            )

        elif not publication.guild_id == interaction_author.guild_id:
            await interaction.message.edit(view=None)

            return await interaction.edit_original_response(
                embed=get_failed_embed("Выпуск с которым вы взаимодействуете был удалён.")
            )

        elif publication.status == status:
            await interaction.message.edit(view=self)

            return await interaction.edit_original_response(
                embed=get_failed_embed(f"Для выпуска **#{publication.publication_number}** уже установлен статус **{status_title.lower()}**")
            )

        await publication_methods.update_publication_by_id(
            publication_id=publication.id,
            column_name="status",
            value=status,
        )

        await action_methods.add_pub_action(
            pub_id=publication.id,
            made_by=interaction_author.id,
            action="setpub_status",
            meta=status,
        )

        embed = await get_publication_profile(publication_id=publication.id)
        view = SetStatus(author=self.author, publication_id=self.publication_id)

        await interaction.message.edit(embed=embed, view=view)

        return await interaction.edit_original_response(
            embed=get_success_embed(f"Вы установили выпуску **#{publication.publication_number}** статус **{status_title.lower()}**.")
        )
