import typer

from nabu.cli.commands import inspect, validate, version
from nabu.cli.debug import debug

app = typer.Typer(no_args_is_help=True)

app.command()(version)
app.command()(validate)
app.command()(inspect)
app.add_typer(debug, name="debug")


def main() -> None:
    app()
