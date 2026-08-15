# Diagnostics, Configuration, and CLI

## Diagnostics

Nabu Forge emits compiler-style diagnostics with error codes, severity, source location, and hints.

Example:

```text
error[E021]: No Python mapping configured for custom scalar 'DateTime'.
  schema.graphqls:14:14
  hint: Add to nabu.toml:
        [scalars]
        DateTime = "datetime.datetime"

warning[E029]: Field 'job' returns polymorphic type 'Job' but has no inline fragments.
  operations/get_job.graphql:3:5
  hint: Add '... on ConcreteType { fields }' for each possible type.
```

**Errors** abort the pipeline after the current stage. **Warnings** print to stderr and the pipeline continues.

### Diagnostic codes

| Code | Severity | Stage    | Meaning                                                |
|------|----------|----------|--------------------------------------------------------|
| E001 | error    | config   | Config file not found                                  |
| E002 | error    | config   | Missing required fields in config                      |
| E003 | error    | config   | Schema path not found                                  |
| E004 | error    | config   | Operations path not found                              |
| E010 | error    | parse    | GraphQL syntax error                                   |
| E011 | error    | parse    | GraphQL validation error                               |
| E012 | error    | parse    | Duplicate type definition                              |
| E013 | error    | parse    | Duplicate operation name                               |
| E020 | error    | semantic | Unknown type reference                                 |
| E021 | error    | semantic | Unmapped custom scalar                                 |
| E022 | error    | semantic | Unknown variable type                                  |
| E023 | error    | semantic | Unknown field / direct field selection on a union type |
| E024 | error    | semantic | Unknown fragment spread                                |
| E025 | error    | semantic | Bad inline fragment target type                        |
| E026 | error    | semantic | Generated Python name collision                        |
| E027 | error    | semantic | Reserved Python name                                   |
| E028 | error    | semantic | Unsupported feature (e.g. subscriptions)               |
| E030 | error    | codegen  | File write error                                       |

---

## Configuration

`nabu.toml` is the single configuration file. All paths are relative to the file's directory.

Minimal configuration:

```toml
schema = "schema.graphqls"
operations = "operations/"
output = "generated_client"
```

With custom scalars:

```toml
schema = "schema.graphqls"
operations = "operations/"
output = "generated_client"

[scalars]
DateTime = "datetime.datetime"
JSON = "typing.Any"
Void = "None"
DependencyReference = "typing.Any"
```

The `[scalars]` table maps GraphQL scalar names to Python type annotation strings. Built-in scalars (`String`, `ID`,
`Int`, `Float`, `Boolean`) are pre-mapped; only custom scalars require configuration. Unmapped custom scalars produce an
E021 error.

---

## Command-Line Interface

The CLI command is `nabu`. All commands accept a `--verbose` / `-v` flag to enable DEBUG logging.

### `nabu version`

Prints the installed version of `nabu-forge`.

### `nabu validate`

Runs the full pipeline (parse → IR → semantic analysis) without writing any files. Useful in CI to validate a schema
change before generation.

```bash
nabu validate --config nabu.toml
```

Output: `OK` on success, diagnostics to stderr on failure.

### `nabu inspect`

Displays a summary of the schema structure.

```bash
nabu inspect --schema schema.graphqls
```

Output:

```
Schema: schema.graphqls

  Object types : 12
  Input types  : 5
  Enums        : 3
  Scalars      : 2
  Interfaces   : 2
  Unions       : 4
  Queries      : 8
  Mutations    : 3
```

### `nabu generate`

Runs the complete compiler pipeline and writes the generated package.

```bash
nabu generate --config nabu.toml
```

Output on success:

```
OK  files=22  written=3  skipped=19  time=1.24s
```

- `files` — total files in the generated package
- `written` — files updated this run (content changed)
- `skipped` — files unchanged from previous run (not touched on disk)
- `time` — wall-clock seconds for code generation + file writes

Files that are identical to the previous generation are not written; their mtime is preserved. This makes
`nabu generate` safe to run in watch mode or CI without unnecessary downstream rebuilds.
