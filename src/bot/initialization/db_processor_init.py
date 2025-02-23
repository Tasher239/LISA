import os
from dotenv import load_dotenv

from database.db_processor import DbProcessor

load_dotenv()

# Инициализация базы данных
db_processor = DbProcessor()
db_processor.init_db()

with db_processor.get_session() as session:
    if session.query(DbProcessor.Server).count() == 0:
        servers = [
            DbProcessor.Server(
                api_url=os.getenv("API_URL"),
                cert_sha256=os.getenv("CERT_SHA"),
                cnt_users=0,
                protocol_type="Outline",
            ),
            DbProcessor.Server(
                ip=os.getenv("VLESS_IP"),
                password=os.getenv("VLESS_PASSWORD"),
                cnt_users=0,
                protocol_type="Vless",
            ),
        ]
        session.add_all(servers)
        session.commit()
