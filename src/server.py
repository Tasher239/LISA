from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn
from bot.initialization.async_outline_processor_init import async_outline_processor
from bot.initialization.db_processor_init import db_processor
from bot.initialization.vless_processor_init import vless_processor
from urllib.parse import quote

app = FastAPI()

def generate_redirect_html(protocol: str, url: str) -> HTMLResponse:
    templates = {
        "outline": f"""
        <html>
            <head>
                <title>Launch Outline</title>
                <meta http-equiv="refresh" content="0; url='{url}'">
            </head>
            <body>
                <script>
                    window.location.href = '{url}';
                    setTimeout(() => window.close(), 30000);
                </script>
                <p>Если Outline не открылся, <a href="{url}">нажмите здесь</a></p>
            </body>
        </html>
        """,
        "vless": f"""
        <html>
            <head>
                <title>Launch Hiddify</title>
                <meta http-equiv="refresh" content="0; url='{url}'">
            </head>
            <body>
                <h2>Hiddify Connection</h2>
                <div style="margin: 20px; padding: 15px; border: 1px solid #ddd;">
                    <p>Ссылка для подключения:</p>
                    <input type="text" value="{url}" 
                           style="width: 100%; padding: 8px; margin: 10px 0;" 
                           id="hiddifyUrl" readonly>
                    <button onclick="navigator.clipboard.writeText('{url}')">
                        Скопировать
                    </button>
                </div>
                <script>
                    // Попытка открыть десктопное приложение
                    window.location.href = '{url}';

                    // Автоматическое закрытие через 30 сек
                    setTimeout(() => window.close(), 30000);
                </script>
            </body>
        </html>
        """
    }
    return HTMLResponse(content=templates[protocol])




def generate_hiddify_url(base_url: str, key_name: str) -> str:
    """Генерирует URL для Hiddify с именем ключа"""
    encoded_url = quote(base_url, safe='')
    encoded_name = quote(key_name.strip())  # Кодируем имя
    return f"hiddify://import/{encoded_url}#{encoded_name}"


@app.get("/open/{key_id}")
async def open_connection(key_id: str):
    try:
        key = db_processor.get_key_by_id(key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")

        protocol = key.protocol_type.lower()

        if protocol == "outline":
            key_info = await async_outline_processor.get_key_info(
                key_id,
                server_id=key.server_id
            )
            url = key_info.access_url

        elif protocol == "vless":
            key_info = await vless_processor.get_key_info(
                key_id,
                server_id=key.server_id
            )
            # Добавляем имя ключа из базы данных
            url = generate_hiddify_url(
                key_info.access_url,
                key.name or f"Key-{key_id[:6]}"  # Используем имя или ID
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported protocol")

        return generate_redirect_html(protocol, url)

    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Error</h1><p>{str(e)}</p>",
            status_code=500
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
