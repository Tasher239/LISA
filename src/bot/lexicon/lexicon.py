from enum import Enum

# Словарь команд
LEXICON_COMMANDS_RU: dict[str, str] = {
    "/command_1": "command_1 description",
    "/command_2": "command_2 description",
    "/command_3": "command_3 description",
    "/command_4": "command_4 description",
}


class Notification(Enum):
    SUBSCRIPTION_REMINDER = (
        "<b>📢 Внимание!</b>\n\n"
        "🔔 <b>Ваша подписка заканчивается через 3 дня!</b>\n\n"
        "🔥 <b>Скидка 20%</b> на продление подписки при оплате до истечения срока действия.\n\n"
        "⏳ Не упустите возможность сэкономить!\n"
        "Выберите удобный для вас период и продлите подписку прямо сейчас.\n\n"
        "<b>💳 Продлить подписку можно в вашем личном кабинете.</b>"
    )

    SUBSCRIPTION_EXPIRED = (
        "<b>⚠️ Внимание!</b>\n\n"
        "❌ <b>Срок вашей подписки истёк.</b>\n\n"
        "🔓 Вы больше не имеете доступа к сервису. Однако вы можете продлить свою подписку и восстановить доступ.\n\n"
        "🔥 <b>Продлите подписку прямо сейчас</b> и воспользуйтесь нашими услугами снова.\n\n"
        "<b>💳 Для продления подписки, перейдите в личный кабинет.</b>"
    )

    SUBSCRIPTION_EXPIRING = (
        "<b>⚠️ Внимание!</b>\n\n"
        "❌ <b>Срок вашей подписки скоро истечет.</b>\n\n"
        "<b>🔑 Ключи, для которых скоро закончится доступ</b>"
    )


class INFO(Enum):
    ABOUT_US = (
        "Здравствуйте! 👋\n\n"
        "Наша команда считает, что знания и доступ к Интернету должны быть безграничными для всех! 🌍\n"
        "Позвольте представить вам бота **LISA (Limitless Internet Safe Access)** — ваш безопасный проводник в мир онлайн-возможностей. 🚀\n\n"
        "💡 **Что умеет LISA?**\n"
        "- **Генерация VPN-ключей** для безопасного и свободного доступа к сети из любой точки планеты.\n"
        "- Удобный **менеджер ключей**, позволяющий легко управлять подключениями.\n"
        "- Полностью **безопасная оплата**: мы и Telegram не храним данные о ваших платежах.\n\n"
        "💬 **Свяжитесь с нами:**\n"
        "Есть вопросы, предложения или хотите сотрудничать? Пишите: @mickpear\n\n"
        "⏳ Не теряйте время! Почувствуйте свободу Интернета с LISA — вашим надежным помощником в сети!✨"
    )

class INSTALL_INSTR(Enum):
    Macbook = (
        "Установка OUTLINE VPN:\n"
        "Для MacOS перейдите по [ссылке](https://apps.apple.com/ru/app/outline-secure-internet-access/id1356178125?mt=12) и установите приложение \n"
        "После установки приложения, зайдите в ваш менеджер ключей и нажмите на Ваш ключ, после чего нажмите на кнопку 'Показать ключ' и скопируйте его\n"
        "Запустите приложение OUTLINE на MAC и вставьте скопиров"


    )