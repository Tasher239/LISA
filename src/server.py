from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from bot.initialization.async_outline_processor_init import async_outline_processor
from bot.initialization.db_processor_init import db_processor

app = FastAPI()


@app.get("/outline/{key_id}")
async def launch_outline(key_id: str):
    key_server_id = db_processor.get_key_by_id(key_id).server_id
    key = await async_outline_processor.get_key_info(key_id, server_id=key_server_id)
    full_key_url = key.access_url

    # Возвращаем HTML с JavaScript для открытия схемы
    html_content = f"""
    <html>
        <head>
            <title>Launch Outline</title>
        </head>
        <body>
            <script>
                window.location.href = '{full_key_url}';
                setTimeout(function() {{
                    window.close();
                }}, 30000);
            </script>
            <p>If Outline didn't open, <a href="{full_key_url}">click here</a></p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
