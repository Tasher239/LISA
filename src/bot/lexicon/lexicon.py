from enum import Enum


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
        "Мы в LISA уверены, что доступ к знаниям и свободный Интернет должны быть доступны каждому! 🌍\n"
        "Позвольте представить вам бота **LISA (Limitless Internet Safe Access)** — вашего безопасного проводника в мир онлайн-возможностей. 🚀\n\n"
        "💡 **Что предлагает LISA?**\n"
        "- **Генерация VPN-ключей** для безопасного и свободного доступа к Интернету из любой точки мира.\n"
        "- Удобный **менеджер ключей**, который помогает легко управлять вашими подключениями.\n"
        "- Полностью **безопасные платежи**: мы и Telegram не храним данные о ваших платежах, гарантируя высокий уровень конфиденциальности.\n\n"
        "📊 **Аналитика использования:**\n"
        "Мы провели собственное исследование, которое показало, что среднее использование VPN-ключа составляет около 100 ГБ в месяц. "
        "Исходя из этого, для каждого ключа установлен лимит в **200 ГБ** в месяц — это в два раза больше среднего, что позволяет нам обеспечить "
        "стабильную работу системы даже при высокой нагрузке. Лимит автоматически обновляется каждый месяц, что гарантирует, что вы всегда получаете "
        "достаточный объем данных для комфортного использования сервиса.\n\n"
        "💬 **Свяжитесь с нами:**\n"
        "Если у вас возникнут вопросы или предложения, пишите: [@lisa_helper](https://t.me/lisa_helper)\n\n"
        "⏳ Откройте для себя мир безграничного доступа к Интернету с LISA — вашим надежным помощником в сети!✨"
    )


INSTALL_INSTR = {
    "VLESS_MacOS": (
        "🔹 **Установка и настройка VLESS на MacOS**\n\n"
        "1️⃣ Установите **V2Ray** через Homebrew:\n"
        "   ```bash\n"
        "   brew install v2ray\n"
        "   ```\n"
        "2️⃣ Загрузите конфигурационный файл с сервера или получите параметры подключения.\n"
        "3️⃣ Переместите файл `config.json` в `/usr/local/etc/v2ray/config.json`.\n"
        "4️⃣ Запустите V2Ray командой:\n"
        "   ```bash\n"
        "   v2ray -config /usr/local/etc/v2ray/config.json\n"
        "   ```\n"
        "5️⃣ Настройте прокси в системе или используйте **ClashX**."
    ),
    "VLESS_iPhone": (
        "🔹 **Установка и настройка VLESS на iPhone (iOS)**\n\n"
        "1️⃣ Установите приложение **Shadowrocket** или **Quantumult X** из App Store.\n"
        "2️⃣ Добавьте новый сервер, выбрав **VLESS**.\n"
        "3️⃣ Введите данные сервера:\n"
        "   - **Адрес** (IP или домен сервера)\n"
        "   - **Порт**: `443`\n"
        "   - **UUID** (уникальный ключ)\n"
        "   - **Transport**: TCP или Reality\n"
        "4️⃣ Сохраните конфигурацию и подключитесь."
    ),
    "VLESS_Windows": (
        "🔹 **Установка и настройка VLESS на Windows**\n\n"
        "1️⃣ Скачайте **V2RayN** с [GitHub](https://github.com/2dust/v2rayN/releases).\n"
        "2️⃣ Установите и запустите программу.\n"
        "3️⃣ Перейдите в **Настройки → Серверы → Добавить сервер**.\n"
        "4️⃣ Введите данные:\n"
        "   - **Адрес сервера**\n"
        "   - **UUID**\n"
        "   - **Порт**: `443`\n"
        "   - **Транспорт**: TCP\n"
        "   - **Security**: Reality (если используется)\n"
        "5️⃣ Сохраните настройки и нажмите **Подключиться**."
    ),
    "VLESS_Android": (
        "🔹 **Установка и настройка VLESS на Android**\n\n"
        "1️⃣ Установите **V2RayNG** из Google Play.\n"
        "2️⃣ Откройте приложение и добавьте новый сервер.\n"
        "3️⃣ Введите настройки VLESS:\n"
        "   - **Адрес сервера**\n"
        "   - **UUID**\n"
        "   - **Порт**: `443`\n"
        "   - **Транспорт**: TCP / Reality\n"
        "4️⃣ Сохраните и нажмите **Start**."
    ),
    "Outline_MacOS": (
        "🔹 **Установка и настройка Outline VPN на MacOS**\n\n"
        "1️⃣ Установите **Outline VPN Client** из App Store: \n"
        "   [Скачать](https://apps.apple.com/ru/app/outline-secure-internet-access/id1356178125?mt=12)\n"
        "2️⃣ Откройте приложение и нажмите **Добавить сервер**.\n"
        "3️⃣ Вставьте полученный **ключ** (формат: `ss://...`).\n"
        "4️⃣ Подключитесь и пользуйтесь интернетом без ограничений."
    ),
    "Outline_iPhone": (
        "🔹 **Установка и настройка Outline VPN на iPhone (iOS)**\n\n"
        "1️⃣ Скачайте **Outline** из App Store: \n"
        "   [Скачать](https://apps.apple.com/us/app/outline-app/id1356177741)\n"
        "2️⃣ Откройте приложение и добавьте сервер.\n"
        "3️⃣ Вставьте полученный ключ и подключитесь."
    ),
    "Outline_Windows": (
        "🔹 **Установка и настройка Outline VPN на Windows**\n\n"
        "1️⃣ Скачайте **Outline Client** с официального сайта: \n"
        "   [Скачать](https://getoutline.org)\n"
        "2️⃣ Установите программу и откройте её.\n"
        "3️⃣ Вставьте ключ подключения.\n"
        "4️⃣ Нажмите **Подключиться** и пользуйтесь интернетом."
    ),
    "Outline_Android": (
        "🔹 **Установка и настройка Outline VPN на Android**\n\n"
        "1️⃣ Установите **Outline VPN** из Google Play.\n"
        "2️⃣ Откройте приложение и нажмите **Добавить сервер**.\n"
        "3️⃣ Вставьте ключ подключения.\n"
        "4️⃣ Подключитесь и начните использовать VPN."
    ),
}


def get_plural_form(number, singular, few, many):
    if 11 <= number % 100 <= 19:
        return many
    last_digit = number % 10
    if last_digit == 1:
        return singular
    elif 2 <= last_digit <= 4:
        return few
    else:
        return many


def get_day_by_number(number):
    return get_plural_form(number, "день", "дня", "дней")


def get_month_by_number(number):
    return get_plural_form(number, "месяц", "месяца", "месяцев")
