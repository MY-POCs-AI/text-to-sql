
from rich.console import Console
from rich.table import Table


console = Console()


def display_results(results):

    # Aucun résultat
    if not results:
        console.print("[yellow]Aucun résultat trouvé.[/yellow]")
        return

    # Création du tableau
    table = Table(title="Résultats SQL")

    # Récupération des colonnes depuis le premier résultat
    columns = results[0].keys()

    for column in columns:
        table.add_column(str(column), overflow="fold")

    # Ajout des lignes
    for row in results:
        values = [str(value) if value is not None else "NULL"
                  for value in row.values()]
        table.add_row(*values)

    # Affichage
    console.print(table)

    # Nombre de résultats
    console.print(
        f"\n[bold green]{len(results)} ligne(s) retournée(s).[/bold green]"
    )
