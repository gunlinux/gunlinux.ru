from fastapi.templating import Jinja2Templates

from app.core.settings import get_settings

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["settings"] = get_settings()  # pyright: ignore[reportArgumentType]
