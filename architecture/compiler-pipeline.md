# Compiler Pipeline

Nabu Forge implements a four-stage compiler pipeline. Each stage has a single responsibility and communicates with the
next via a well-defined data structure.

---

## Stage 1 — Parse

**Input:** paths to SDL file and operation `.graphql` files  
**Output:** `GraphQLSchema` + `list[DocumentNode]`  
**Library:** `graphql-core >= 3.2`

Responsibilities:

- Lexical analysis and parsing of GraphQL SDL
- Construction of the GraphQL schema model
- Parsing of operation documents
- Validation of operations against the schema (field existence, argument types, fragment compatibility)

Errors at this stage have codes E010–E013.

---

## Stage 2 — Build IR

**Input:** `GraphQLSchema` + `list[DocumentNode]`  
**Output:** `IRDocument`  
**Module:** `nabu.ir.transformer`

The IR (Intermediate Representation) is the project's internal schema model, completely independent of `graphql-core`.
No graphql types cross this boundary into later stages.

Key IR types:

| IR type            | Description                                                      |
|--------------------|------------------------------------------------------------------|
| `NamedTypeRef`     | A named leaf type (String, MyEnum, etc.)                         |
| `ListTypeRef`      | A list wrapper around another TypeRef                            |
| `NonNullTypeRef`   | A non-null wrapper around another TypeRef                        |
| `IRObjectType`     | A GraphQL object type with fields and interface list             |
| `IRInterfaceType`  | A GraphQL interface                                              |
| `IRUnionType`      | A GraphQL union and its member type names                        |
| `IREnumType`       | An enum with its values                                          |
| `IRInputType`      | An input object type                                             |
| `IRScalarType`     | A scalar (builtin flag + name)                                   |
| `IROperation`      | A query or mutation with variables and selections                |
| `IRFragment`       | A named fragment definition                                      |
| `IRFieldSelection` | A field selected in an operation (with alias and sub-selections) |
| `IRInlineFragment` | An inline `... on TypeName { }` fragment                         |
| `IRFragmentSpread` | A `...FragmentName` spread                                       |

`IRDocument` carries all of the above in typed lists (`objects`, `inputs`, `enums`, `scalars`, `interfaces`, `unions`,
`operations`, `fragments`, `query_fields`, `mutation_fields`).

---

## Stage 3 — Semantic Analysis

**Input:** `IRDocument` + `Config`  
**Output:** `IRDocument` (same, unchanged) + diagnostics  
**Module:** `nabu.analysis.analyser`

Validates project-specific constraints that go beyond what GraphQL syntax validation covers:

| Check                                        | Codes     |
|----------------------------------------------|-----------|
| All type references resolve to defined types | E020      |
| Custom scalars have a `[scalars]` mapping    | E021      |
| Operation variables reference defined types  | E022      |
| Selected fields exist on their parent types  | E023      |
| Fragment spreads reference defined fragments | E024      |
| Inline fragment targets are defined types    | E025      |
| Generated Python names do not collide        | E026–E027 |
| Subscriptions are rejected (not supported)   | E028      |

The `IRIndex` class provides O(1) type and field lookup across the IR during analysis.

---

## Stage 4 — Code Generation

**Input:** `IRDocument` + `Config`  
**Output:** `dict[str, str]` (relative path → source code)  
**Modules:** `nabu.backends.python.codegen.*`

Each generator produces one file:

| Generator        | Output file            | Content                                            |
|------------------|------------------------|----------------------------------------------------|
| `enum_gen`       | `enums.py`             | `str, Enum` classes                                |
| `input_gen`      | `inputs.py`            | Pydantic v2 input models                           |
| `model_gen`      | `models.py`            | Pydantic v2 schema models + union aliases          |
| `scalars_gen`    | `scalars.py`           | `SCALAR_MAP` dict                                  |
| `transport_gen`  | `transport.py`         | `Transport(url, headers, timeout)` class           |
| `exceptions_gen` | `exceptions.py`        | `GraphQLResponseError`                             |
| `client_gen`     | `client.py`            | `Client` class with one async method per operation |
| `exports_gen`    | `__init__.py`          | Re-exports all public types and `Client`           |
| `operation_gen`  | `operations/<name>.py` | `<Op>Result` + nested model classes                |

Templates are Jinja2 files in `nabu/backends/python/codegen/templates/`. After rendering, each file is passed through
`ruff check --select F --fix` (remove unused imports) then `ruff format` (formatting). All generated files are
ruff-clean.

### Key design decisions

**camelCase → snake_case aliasing.** Every field whose wire name differs from its Python name gets
`Field(alias="wireName")` and its class gets `model_config = ConfigDict(populate_by_name=True)`. Input models serialize
with `model_dump(by_alias=True)` so wire names are sent to the server.

**Discriminated union for polymorphic types.** When a field returns a union or interface and inline fragments are
present, the generator produces one member class per fragment (each with
`typename: Literal["TypeName"] = Field(alias="__typename")`), then a module-level
`Annotated[A | B, Field(discriminator="typename")]` alias. `__typename` is injected automatically into the sent GraphQL
document via `_inject_typename` in `client_gen`.

**Shared interface fields.** Fields selected at the interface level alongside `... on` fragments are prepended to every
member class's selection. Users do not need to repeat shared fields inside each fragment.

**Fragment inlining.** Named fragment spreads are fully resolved at code-generation time. The `_inline_fragments` pass
replaces every `IRFragmentSpread` with the fragment's selections before walking the selection tree.

**Deterministic output.** Generation order is controlled by `dependency_order` (topological sort over field types).
Declaration-order lists prevent PYTHONHASHSEED-sensitive output.

**`_GenContext` for recursive generation.** The `_selection_fields` function carries seven invariant parameters in a
frozen `_GenContext` dataclass. Only the three varying parameters (selections, parent_type, prefix) are passed at each
recursive call site.
