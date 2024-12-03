from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
    create_engine,
    Table,
    MetaData,
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime, timedelta
from logger.logging_config import setup_logger
from bot.initialization.bot_init import bot
from bot.keyboards.keyboards import get_prodlit_keyboard
from bot.fsm.states import GetKey
import asyncio
from aiogram.fsm.context import FSMContext

logger = setup_logger()

# Создаем базовый класс для моделей
Base = declarative_base()


class DbProcessor:
    def __init__(self):
        # Создаем движок для подключения к базе данных
        self.engine = create_engine("sqlite:///vpn_users.db", echo=True)
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self):
        """Синхронная инициализация базы данных."""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Создает и возвращает новую сессию."""
        return self.Session()

    def update_database_with_key(self, user_id, key, period):
        session = self.get_session()
        try:
            user_id_str = str(user_id)
            user = (
                session.query(DbProcessor.User)
                .filter_by(user_telegram_id=user_id_str)
                .first()
            )
            if not user:
                user = DbProcessor.User(
                    user_telegram_id=user_id_str,
                    subscription_status="active",
                    use_trial_period=False,
                )
                session.add(user)
                session.commit()

            period_months = int(period.split()[0])
            start_date = datetime.now()
            expiration_date = start_date + timedelta(days=30 * period_months)
            new_key = DbProcessor.Key(
                key_id=key.key_id,
                user_telegram_id=user_id_str,
                expiration_date=expiration_date,
                start_date=start_date,
            )
            session.add(new_key)
            session.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления базы данных: {e}")
            raise
        finally:
            session.close()

    async def check_db(self):
        while (True):
            await asyncio.sleep(60 * 60 * 12) # каждые 12 ч
            session = self.get_session()
            try:
                users = session.query(DbProcessor.User).all()
                for user in users:
                    for key in user.keys:
                        if (key.remembering == False) and (key.expiration_date - datetime.now() < timedelta(days=3)):
                            key.remembering = True
                            session.commit()
                            await bot.send_message(
                                user.user_telegram_id,
                                "<b>📢 Внимание!</b>\n\n"
                                "🔔 <b>Ваша подписка заканчивается через 3 дня!</b>\n\n"
                                "🔥 <b>Скидка 20%</b> на продление подписки при оплате до истечения срока действия.\n\n"
                                "⏳ Не упустите возможность сэкономить!\n"
                                "Выберите удобный для вас период и продлите подписку прямо сейчас.\n\n"
                                "<b>💳 Продлить подписку можно в вашем личном кабинете.</b>",
                                parse_mode="HTML",
                                reply_markup=get_prodlit_keyboard()
                            )
                        elif key.expiration_date < datetime.now():
                            await bot.send_message(
                                user.user_telegram_id,
                                "<b>⚠️ Внимание!</b>\n\n"
                                "❌ <b>Срок вашей подписки истёк.</b>\n\n"
                                "🔓 Вы больше не имеете доступа к сервису. Однако вы можете продлить свою подписку и восстановить доступ.\n\n"
                                "🔥 <b>Продлите подписку прямо сейчас</b> и воспользуйтесь нашими услугами снова.\n\n"
                                "<b>💳 Для продления подписки, перейдите в личный кабинет.</b>",
                                parse_mode="HTML",
                                reply_markup=get_prodlit_keyboard(),  # Клавиатура для продления подписки
                            )
                        elif datetime.now() > key.expiration_date + timedelta(days=1):
                            session.delete(key)
                            session.commit()
            except Exception as e:
                logger.error(f"Ошибка проверки базы данных: {e}")
                raise


    # Определение таблицы Users
    class User(Base):
        __tablename__ = "users"
        user_telegram_id = Column(String, primary_key=True)  # Telegram ID пользователя
        subscription_status = Column(String)  # Статус подписки (active/inactive)
        use_trial_period = Column(Boolean)  # Использован ли пробный период
        # Отношение с таблицей Keys (один ко многим)
        keys = relationship("Key", back_populates="user", cascade="all, delete-orphan")

    # Определение таблицы Keys
    class Key(Base):
        __tablename__ = "keys"
        key_id = Column(String, primary_key=True)  # id ключа в outline и бд
        user_telegram_id = Column(
            String, ForeignKey("users.user_telegram_id")
        )  # ID пользователя (ссылка на пользователя)
        # Обратное отношение к таблице Users
        expiration_date = Column(DateTime)  # Дата окончания подписки
        start_date = Column(DateTime)  # Дата начала подписки
        user = relationship("User", back_populates="keys")
        remembering_before_exp = Column(Boolean, default=False) # напомнить о продлении 1 раз


