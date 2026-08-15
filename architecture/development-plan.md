# Development Plan

Implementation was carried out in eleven phases. Phases 1–10 are complete.
Phase 11 adds quality-of-life improvements and euporie-specific auth.

---

## Phase 1: Project foundation ✅

- Repository structure, packaging, CLI entry point
- Config loading (`nabu.toml`)
- Diagnostics system
- GraphQL file loading

```bash
nabu version
nabu validate
```

---

## Phase 2: Parsing and schema loading ✅

- Schema parsing via `graphql-core`
- Operation parsing and validation against schema
- Schema inspection command

```bash
nabu inspect --schema schema.graphqls
```

---

## Phase 3: Symbol table ✅

- Symbol registration and type lookup
- Duplicate detection
- Interface implementation and union member lookup
- Fragment registration

Implemented as `IRIndex` inside the analysis layer rather than a standalone symbol-table class.

---

## Phase 4: Intermediate representation ✅

- IR type definitions (`NamedTypeRef`, `ListTypeRef`, `NonNullTypeRef`)
- AST-to-IR transformer (`build_ir`)
- Operation IR with inline fragments, named fragments, aliases
- Source location preservation
- `graphql-core` firewall: no graphql types past the IR layer

---

## Phase 5: Semantic analysis ✅

- Type-reference validation (E020)
- Custom scalar validation (E021)
- Variable type validation (E022)
- Selection set validation (E023–E025)
- Naming collision detection (E026–E027)
- Unsupported-feature diagnostics (E028)
- Polymorphic-field-without-fragments warning (E029)

---

## Phase 6: Python type mapping ✅

- Built-in scalar mappings (String, ID, Int, Float, Boolean)
- Custom scalar configuration via `[scalars]`
- Nullability and list conversion (all 8 combinations)
- camelCase → snake_case with `Field(alias=...)`
- Import tracking via `ImportCollector`

---

## Phase 7: Model generation ✅

- Enums (`str, Enum`)
- Input models (with alias + `model_config`)
- Schema models in dependency order
- Union type aliases in `models.py`
- Scalar helpers
- Package exports (`__init__.py`)

---

## Phase 8: Client generation ✅

- Async client methods per operation
- GraphQL document constants (one per operation, fragments inlined)
- Variable serialization (`_serialize` handles Enum, BaseModel)
- `model_validate(response["data"])` deserialization
- `GraphQLResponseError` on server errors
- `by_alias=True` in `model_dump` so inputs serialize to wire names

---

## Phase 9: Interfaces, unions, and fragments ✅

- Named fragments inlined before codegen
- Inline fragments → discriminated union alias
- `__typename` injected automatically in the sent document
- `Literal["TypeName"]` discriminator field on each member class
- `model_config = ConfigDict(populate_by_name=True)` on aliased classes
- Shared interface-level fields emitted into every union member class
- Polymorphic warning (E029) when no inline fragments present

---

## Phase 10: Quality and validation ✅

- 144 unit + integration tests
- `ruff check --select F` and `ruff format` enforced in the render engine
- Deterministic output (PYTHONHASHSEED-stable generation order)
- End-to-end tests importing the generated package
- Both `university` and `euporie` samples generate and import cleanly

---

## Phase 11: Refactor, auth, and QoS ✅

### Readability refactors (no output change)
- `engine.py`: unified `_run_ruff` helper (fixed stdout-vs-returncode asymmetry)
- `fields.py`: `build_class_spec()` extracts the duplicated model-building loop from `model_gen` and `input_gen`
- `operation_gen.py`: `_GenContext` dataclass collapses 9-arg `_selection_fields` to 4-arg
- `operation_model.py.jinja`: template consumes `ClassSpec`/`UnionSpec` dataclasses directly; dict-conversion block deleted

### Feature fixes
- **Shared interface fields**: fields selected at the interface level are prepended to every fragment's selection in the polymorphic branch — no more manual repetition in each `... on` block
- **Aliased-field fix**: explicit `sel.alias` always emits `Field(alias=...)` even when the alias is already snake_case; two aliases of the same field produce distinct Python fields
- **Transport**: persistent `httpx.AsyncClient`, configurable `timeout=30.0`, `aclose()`, `Client.__aenter__/__aexit__`
- **Compilation metrics**: `OK  files=22  written=3  skipped=19  time=1.24s` in CLI output

### Euporie auth (`samples/euporie/euporie_auth.py`)
- `client_from_secret_key(path)` — UAA bearer JWT via clientid + clientsecret
- `client_from_cert_key(path)` — mTLS certificate auth with `MtlsTransport`
- In-memory token caching with 60s expiry buffer
- Reads SAP BTP service key JSON directly

---

## Deferred (future work)

- `@skip` / `@include` directive support
- Variable default values in client method signatures
- `@deprecated` capture and codegen warnings
- Docstrings from GraphQL schema descriptions
- `py.typed` marker and `__all__` in generated packages
- CI pipeline (GitHub Actions)
- Subscriptions (explicitly out of scope for MVP)
