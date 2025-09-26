"""Custom CLI commands for the blog application."""

from typing import TYPE_CHECKING

import click
from flask.cli import with_appcontext
from blog.extensions import db
from blog.user.models import User

if TYPE_CHECKING:
    from flask import Flask


@click.command("create-admin")  # Add this decorator to make it a Click command
@click.option("--name", prompt="Username", help="The username for the admin user")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="The password for the admin user",
)
@with_appcontext
def create_admin(name: str, password: str) -> None:
    """Create an admin user with the given username and password."""
    # Check if user already exists
    existing_user = db.session.execute(
        db.select(User).where(User.name == name)
    ).scalar_one_or_none()

    if existing_user:
        click.echo("User '{}' already exists.".format(name))
        return

    # Create new user
    user = User(name=name)
    user.set_password(password)

    # Add to database
    db.session.add(user)
    db.session.commit()

    click.echo("Admin user '{}' created successfully.".format(name))


def init_app(app: "Flask") -> None:
    """Initialize the CLI commands with the Flask app."""
    app.cli.add_command(create_admin)
