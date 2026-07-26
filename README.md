# Nabu Forge

A schema-driven compiler that transforms GraphQL SDL and operation definitions into type-safe Python client packages.

```text
GraphQL SDL + operations  ->  Nabu Forge  ->  Typed Python client package
```

## What it does

Given a GraphQL schema and operation documents, Nabu Forge generates a complete Python package with:

- Typed Pydantic models for every response shape
- Enum definitions
- Input models
- Async client methods with variable serialization and response deserialization
- Custom scalar mappings
- HTTP transport integration

### Example generated usage

```python
from generated_client import Client

client = Client(url="https://example.com/graphql", headers={"Authorization": "Bearer token"})

student = await client.get_student(student_id="123")
print(student.id)
print(student.status)
```

## Installation

```bash
pip install nabu-forge
```

Or for development:

```bash
git clone https://github.com/yourname/nabu-forge
cd nabu-forge
pip install -e .
```

## Usage

Create a `nabu.toml` in your project root:

```toml
schema = "schema.graphqls"
operations = "operations/"
output = "generated_client"

[scalars]
DateTime = "datetime.datetime"
JSON = "typing.Any"
```

Then run:

```bash
# Check your config and file paths
nabu validate

# Generate the client package
nabu generate
```

## Configuration

| Field        | Description                                     |
|--------------|-------------------------------------------------|
| `schema`     | Path to your GraphQL SDL file                   |
| `operations` | Directory containing `.graphql` operation files |
| `output`     | Output directory for the generated package      |
| `[scalars]`  | Python type mappings for custom scalars         |

## Compiler pipeline

Nabu Forge is a full compiler with eight stages:

1. **Parse** – `graphql-core` parses SDL and operation documents into an AST
2. **Symbol table** – all types, fields, enums, interfaces, unions, and operations are registered and cross-referenced
3. **Semantic analysis** – validates type references, scalar mappings, operation variables, and fragment compatibility
4. **Intermediate representation** – AST is transformed into a project-specific IR independent of `graphql-core`
5. **Type mapping** – GraphQL types are translated into Python annotations, including full nullability handling
6. **Code generation** – IR is rendered into formatted Python source files

### GraphQL -> Python type mapping

| GraphQL      | Python                      |
|--------------|-----------------------------|
| `String!`    | `str`                       |
| `String`     | `str \| None`               |
| `[String!]!` | `list[str]`                 |
| `[String]`   | `list[str \| None] \| None` |
| `Int!`       | `int`                       |
| `Float!`     | `float`                     |
| `Boolean!`   | `bool`                      |
| `ID!`        | `str`                       |

## MVP scope

Supported in the first release:

- Object types, input types, enums, built-in scalars, custom scalars
- Queries and mutations
- Lists and nullability
- Pydantic models, async HTTP client
- Basic diagnostics

Not yet supported: subscriptions, federation, file uploads, schema extensions, sync clients.

## Development

```bash
pip install -e .
pip install pytest ruff

ruff check src/
pytest
```

## Architecture docs

- [`architecture/overview.md`](architecture/overview.md) - project summary and goals
- [`architecture/compiler-pipeline.md`](architecture/compiler-pipeline.md) - all eight pipeline stages
- [`architecture/generated-package.md`](architecture/generated-package.md) - generated package layout
- [`architecture/diagnostics-and-cli.md`](architecture/diagnostics-and-cli.md) - CLI and diagnostics design
- [`architecture/development-plan.md`](architecture/development-plan.md) - ten implementation phases
- [`architecture/product-requirements.md`](architecture/product-requirements.md) - MVP scope and definition of done
