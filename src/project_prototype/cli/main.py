import sys
from datetime import timedelta
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console

from project_prototype.cli import (
    avif_app,
    jpeg2000_app,
    jpeg_app,
    jpegxl_app,
    webp_app,
)

main_app = typer.Typer()
console = Console()

main_app.add_typer(avif_app, name="avif")
main_app.add_typer(jpeg2000_app, name="jpeg2000")
main_app.add_typer(jpeg_app, name="jpeg")
main_app.add_typer(jpegxl_app, name="jpegxl")
main_app.add_typer(webp_app, name="webp")

PROJECT_NAME = "project-prototype"


def debug_callback(*, value: bool) -> None:
    if value:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        # Disable logs.
        logger.remove()
        logger.add(sys.stderr, level="CRITICAL")


def version_callback(*, value: bool) -> None:
    if value:
        try:
            version = package_version(PROJECT_NAME)
        except PackageNotFoundError:
            version = "unknown"

        typer.echo(f"{PROJECT_NAME} {version}")
        raise typer.Exit(0)


@main_app.callback(invoke_without_command=True)
def main(
    *,
    version: Annotated[  # noqa: ARG001
        bool | None,
        typer.Option(
            "-V",
            "--version",
            help="Display app's version",
            is_eager=True,
            callback=version_callback,
        ),
    ] = None,
    debug: Annotated[  # noqa: ARG001
        bool,
        typer.Option(
            "--debug",
            callback=debug_callback,
            help="Enable debug logging",
        ),
    ] = False,
) -> None:
    logger.add(
        "logs/",
        retention=timedelta(days=30),
        enqueue=True,
    )


if __name__ == "__main__":
    main_app()
