# Nabu Forge

**Nabu Forge** is a schema-driven compiler and code-generation tool that transforms GraphQL schemas and operation definitions into type-safe Python client packages.

## Architecture

The detailed design is split across the [`architecture/`](architecture/) directory:

- [Overview](architecture/overview.md) — project summary, primary goal, and example usage.
- [Compiler Pipeline](architecture/compiler-pipeline.md) — the eight pipeline stages, from SDL input through code generation.
- [Generated Package](architecture/generated-package.md) — generated package layout, models, enums, inputs, client methods, interfaces/unions, and naming.
- [Diagnostics and CLI](architecture/diagnostics-and-cli.md) — compiler diagnostics, `nabu.toml` configuration, and the `nabu` command-line interface.
- [Development Plan](architecture/development-plan.md) — the ten implementation phases.
- [Product Requirements](architecture/product-requirements.md) — MVP scope, final requirements, definition of done, and project classification.
