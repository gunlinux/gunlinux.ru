from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from app.auth.jwt import decode_token
from app.core.dependencies import UserServiceDep
from app.domain.user import User


async def get_current_user(
    user_service: UserServiceDep,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = access_token.removeprefix("Bearer ")
    username = decode_token(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = await user_service.get_user_by_name(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
