from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse

from app.auth.jwt import COOKIE_NAME, create_access_token
from app.core.dependencies import UserServiceDep
from app.core.templates import templates

router = APIRouter(prefix="/auth")


@router.get("/login")
async def login_form(request: Request) -> Response:
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(
    request: Request,
    user_service: UserServiceDep,
    username: str = Form(...),
    password: str = Form(...),
) -> Response:
    user = await user_service.authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid username or password"},
            status_code=401,
        )
    token = create_access_token(user.name)
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=f"Bearer {token}",
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout() -> Response:
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key=COOKIE_NAME)
    return response
