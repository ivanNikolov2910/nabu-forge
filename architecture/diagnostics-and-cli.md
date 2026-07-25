# Diagnostics, Configuration, and CLI

## Diagnostics

Nabu Forge should provide compiler-style diagnostics.

Diagnostics should include:

* error code;
* severity;
* source file;
* line and column;
* explanation;
* suggested correction.

Example:

```text
error[NF2001]: Unknown GraphQL type "Timestamp".

  schema.graphql:22:14
    createdAt: Timestamp!
               ^^^^^^^^^

Define the scalar in the schema or configure an existing scalar mapping.
```

Diagnostic categories may include:

* syntax errors;
* schema errors;
* semantic errors;
* unsupported features;
* configuration errors;
* generation errors;
* file-system errors.

---

## Configuration

The generator should support a project configuration file.

Example `nabu.toml`:

```toml
schema = "schema.graphqls"
operations = "operations"
output = "generated_client"
package_name = "generated_client"

async_client = true
model_library = "pydantic"

[scalars]
DateTime = "datetime.datetime"
JSON = "typing.Any"
Void = "None"

[naming]
field_case = "snake_case"
enum_case = "preserve"
```

---

## Command-Line Interface

The CLI command should be `nabu`.

Example:

```bash
nabu generate \
    --schema schema.graphqls \
    --operations operations/ \
    --output generated_client/
```

Additional commands may include:

```bash
nabu validate
nabu inspect
nabu generate
nabu clean
nabu version
```

### `nabu validate`

Validates:

* the GraphQL schema;
* operation documents;
* scalar mappings;
* semantic constraints;
* generator configuration.

### `nabu inspect`

Displays information about the schema:

* number of object types;
* number of input types;
* available queries;
* available mutations;
* custom scalars;
* interfaces;
* unions.

### `nabu generate`

Runs the complete compiler pipeline and generates the Python package.
