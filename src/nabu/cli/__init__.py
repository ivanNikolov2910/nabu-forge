import typer

from nabu.cli.callbacks import verbose_callback
from nabu.cli.commands import generate, inspect, validate, version

app = typer.Typer(no_args_is_help=True)

app.command()(version)
app.command()(validate)
app.command()(generate)
app.command()(inspect)

app.callback()(verbose_callback)


def main() -> None:
    app()
