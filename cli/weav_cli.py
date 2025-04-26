import typer
import logging
from weaviate_layer.collections import ensure_collections_exist
from weaviate_layer.manage_collections import (
    create_basic, create_text2vec_openai, list_all,
    get_config, drop, ingest_rows
)

logging.basicConfig(level=logging.INFO)

app = typer.Typer()
weav = typer.Typer(help="Manage Weaviate collections (v4)")
app.add_typer(weav, name="weav")

@weav.command("create")
def create(
    name: str = typer.Argument(...),
    openai: bool = typer.Option(
        False, "--openai", help="Use text2vec-openai with TEXT-3-Large"
    ),
):
    """Create a new collection."""
    if openai:
        create_text2vec_openai(name)
    else:
        create_basic(name)

@weav.command("list")
def _list(simple: bool = typer.Option(True, help="Return only collection names")):
    """Show all collections."""
    typer.echo(list_all(simple))

@weav.command("show")
def show(name: str):
    """Get full config for one collection."""
    typer.echo(get_config(name))

@weav.command("drop")
def _drop(
    name: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm destructive drop"),
):
    """Delete collection(s) and their data."""
    drop(name, yes_i_know=yes)

@weav.command("ingest")
def ingest(
    name: str,
    jsonl_path: str = typer.Argument(..., help="Path to JSON-Lines file"),
):
    """Bulk-ingest objects from a JSON-Lines file."""
    import json, pathlib
    rows = (json.loads(line) for line in pathlib.Path(jsonl_path).read_text().splitlines())
    ingest_rows(name, rows)

@weav.command("ensure-collections")
def ensure_collections():
    """
    Ensures all defined Weaviate collections exist in the connected instance.
    """
    logging.info("Running 'ensure-collections' command...")
    try:
        ensure_collections_exist()
        logging.info("'ensure-collections' command finished successfully.")
    except Exception as e:
        logging.error(f"Error during 'ensure-collections': {e}")
        raise typer.Exit(code=1)

# Keep the original create-collections command commented out for now
# @app.command()
# def create_collections():
#     """
#     Ensures all defined Weaviate collections exist.
#     """
#     logging.info("Running 'create collections' command...")
#     try:
#         ensure_collections_exist()
#         logging.info("'create collections' command finished successfully.")
#     except Exception as e:
#         logging.error(f"Error during 'create collections': {e}")
#         raise typer.Exit(code=1)


if __name__ == "__main__":
    app()