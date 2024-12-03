def get_instruction_string(key_access_url: str) -> str:
    instructions = (
        "📖 Инструкция по установке VPN:\n\n"
        "1. Скачайте приложение OutLine:\n"
        "   - Для Android: [Ссылка на Google Play](https://play.google.com/store/apps/details?id=org.outline.android.client&hl=ru)\n"
        "   - Для iOS: [Ссылка на App Store](https://apps.apple.com/ru/app/outline-app/id1356177741)\n"
        "   - Для Windows/Mac: [Ссылка на сайт](https://example.com)\n\n"
        "2. Откройте приложение и введите следующие данные:\n"
        f"```\n"
        f"{key_access_url}\n"
        f"```"
        "3. Подключитесь и наслаждайтесь безопасным интернетом! 🎉"
    )
    return instructions


def get_your_key_string(key, text="Ваш ключ от VPN") -> str:
    return f"{text}\n```\n" f"{key.access_url}\n```"
