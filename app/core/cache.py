import json
from typing import override

from fastapi import Request, Response
from fastapi_cache.coder import Coder


class ResponseCoder(Coder):
    """Serializes starlette Response objects by body content."""

    @override
    @classmethod
    def encode(cls, value: object) -> bytes:
        if isinstance(value, Response):
            body = value.body
            body_str = body.decode("utf-8") if isinstance(body, bytes) else (body or "")
            return json.dumps(
                {
                    "_r": True,
                    "b": body_str,
                    "s": value.status_code,
                    "m": value.media_type or "text/html",
                }
            ).encode()
        return json.dumps(value).encode()

    @override
    @classmethod
    def decode(cls, value: bytes) -> object:
        data = json.loads(value)
        if isinstance(data, dict) and data.get("_r"):
            return Response(
                content=data["b"],
                status_code=data["s"],
                media_type=data["m"],
            )
        return data


async def htmx_key_builder(
    func: object,  # pyright: ignore[reportUnusedParameter]
    namespace: str = "",
    request: Request | None = None,
    response: Response | None = None,  # pyright: ignore[reportUnusedParameter]
    args: tuple[object, ...] | None = None,  # pyright: ignore[reportUnusedParameter]
    kwargs: dict[str, object] | None = None,  # pyright: ignore[reportUnusedParameter]
) -> str:
    hx = request.headers.get("HX-Request", "") if request else ""
    url = str(request.url) if request else ""
    return f"{namespace}:{url}:{hx}"
