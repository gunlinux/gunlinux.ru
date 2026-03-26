from pathlib import Path
from typing import TYPE_CHECKING

from flask import Blueprint, Response, abort

if TYPE_CHECKING:
    from flask import Response

robots = Blueprint("robots", __name__)


@robots.route("/robots.txt")
def robots_txt() -> Response | str:
    """Serve the robots.txt file from the project root."""
    # Project root is the parent of the blog directory
    project_root = Path(__file__).parent.parent.parent
    robots_file = project_root / "robots.txt"

    if not robots_file.exists():
        abort(404)

    content = robots_file.read_text()
    return Response(content, mimetype="text/plain")
