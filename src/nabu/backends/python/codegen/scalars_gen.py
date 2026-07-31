from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.config.loader import Config


def generate_scalars(config: Config) -> str:
    scalars = scalar_table(config.scalars)
    collector = ImportCollector()
    entries = []

    for gql_name, annotation in sorted(scalars.items()):
        annotation = collector.add(annotation)
        entries.append((gql_name, annotation))

    return render(
        "scalars.py.jinja",
        {
            "scalars": entries,
            "imports": collector.render(),
        },
    )
