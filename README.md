# LISA (Limitless Internet Safe Access)

## Описание проекта

**LISA** — это чат-бот, предоставляющий пользователям безопасный доступ к ресурсам сети Интернет через VPN. Бот разработан для автоматизации взаимодействия с VPN-сервисом, предоставления ключей доступа, управления подписками и анализа статистики использования. Взаимодействие осуществляется через мессенджер Telegram.

## Особенности
- Полная автоматизация взаимодействия с VPN-сервисом через Telegram.
- Интуитивно понятный интерфейс и лёгкость использования.
- Гибкость управления ключами и подписками.
- Интеграция с безопасными методами оплаты Telegram.
- Возможность получения детальной статистики использования.

## Основные функции:
1. **Генерация ключей доступа** — пользователь может получить ключ для подключения к VPN, выбрав нужный период действия.
2. **Нотификация** — бот уведомляет пользователей об окончании действия подписок и предоставляет возможность их продления.
3. **Оплата** — безопасные платежи внутри Telegram.
4. **Статистика использования** — просмотр объема трафика, средней скорости потребления и других метрик.
5. **Управление ключами** — просмотр активных ключей, их переименование, просмотр, продление, даты окончания активации.
6. **Инструкции** — пошаговая помощь в настройке VPN на различных устройствах (ПК, Android, iOS).


---

## Сценарии использования

1. **Главное меню**
   - Команда: `/start`
   - Предлагает выбор:
     - Получить ключ.
     - Управление ключами.

2. **Получение ключа**
   - Выбор периода действия (1 месяц, 3 месяца, 6 месяцев, 12 месяцев).
   - Оплата через Telegram.
   - После оплаты бот отправляет ключ и инструкцию по использованию.

3. **Управление ключами**
   - Просмотр списка ключей.
   - Возможные действия:
     - Посмотреть объем трафика.
     - Узнать дату окончания действия ключа.
     - Продлить ключ.
     - Переименовать ключ.

4. **Инструкции**
   - Бот предоставляет пошаговую инструкцию по настройке VPN для выбранного устройства (ПК, Android, iOS).

---

## Архитектура проекта



### Используемые технологии:
- **Python** — основной язык разработки.
- **Telegram Bot API** — для взаимодействия с пользователями.
- **SQLAlchemy** — работа с базой данных.
- **Платежные API** — интеграция с платежными системами Telegram.

### Схема базы данных:
**Таблица Users**

|           Поле        | Тип   |             Описание             |
|-----------------------|-------|----------------------------------|
| `user_telegram_id`    | str   | Telegram ID пользователя         |
| `subscription_status` | str   | Статус подписки (active/inactive)|
| `use_trial_period`    | bool  | Использован ли пробный период    |


**Таблица Keys**

| Поле                     | Тип   | Описание                    |
|--------------------------|-------|-----------------------------|
| `key_id`                 | str   | VPN-ключ                    |
| `user_telegram_id`       | str   | Telegram ID пользователя    |
| `expiration_date`        | ISO-86| Дата конца активации ключа  |
| `start_date`             |ISO-86 | Дата начала активации ключа |
| `remembering_before_exp` |bool   | Напоминание перед окончанием срока.  |
---

**Связь таблиц**:
- Тип: один ко многим.
- Поле связи: `user_telegram_id`.
## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/username/LISA.git



