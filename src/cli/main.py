import asyncio

import click
import uvicorn

from src.config import Settings
from src.loader.main import PackageLoader


@click.group()
def cli():
    """ALT Repoteka Service CLI"""
    pass


@cli.command()
def load():
    """Upload data from Repoteka to the database"""
    click.echo("Starting data load...")
    settings = Settings()
    loader = PackageLoader(settings)

    # Создаём асинхронную обёртку, которая выполнит оба метода в ОДНОМ event loop
    async def run_load():
        await loader.init_db()
        await loader.load_all_branches()

    # Запускаем один event loop для обеих операций
    asyncio.run(run_load())

    click.echo("Load completed!")


@cli.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8000)
def serve(host, port):
    # Start the API server
    click.echo(f"Starting API on {host}:{port}")
    uvicorn.run("src.api.main:app", host=host, port=port, reload=False)


@cli.command()
def status():
    # Check the service status
    click.echo("Status: OK (placeholder)")


if __name__ == "__main__":
    cli()
