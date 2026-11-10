import typer

app = typer.Typer()


@app.command()
def jpeg() -> None:
    raise NotImplementedError
