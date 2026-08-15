# Product Requirements

## Minimum Viable Product

The first useful version supports:

- GraphQL SDL parsing via `graphql-core`
- GraphQL operation documents (queries + mutations)
- Object types, input types, enums, scalars, interfaces, unions
- Lists and nullability (all 8 combinations)
- Custom scalars via `[scalars]` config
- Inline fragments and named fragments
- Discriminated unions for polymorphic types (`__typename`)
- Shared interface-level fields alongside inline fragments
- camelCase → snake_case field aliasing with correct wire serialization
- Field aliases (including two aliases of the same underlying field)
- Pydantic v2 models for schema types and operation response types
- Async httpx client with operation methods, variable serialization, response deserialization
- Compiler-style diagnostics with error codes, file/line/column, and hints
- Deterministic, ruff-formatted output

The MVP intentionally excludes:

- Subscriptions
- File uploads (multipart)
- Query batching
- `@skip` / `@include` directives
- Variable default values
- Schema extensions or federation
- Sync clients

---

## Final Product Requirements

Nabu Forge should:

1. Parse GraphQL SDL and operation documents.
2. Validate the schema and operations — clear diagnostics on failure.
3. Build a complete IR independent of `graphql-core`.
4. Perform semantic analysis (type refs, scalars, fields, fragments, naming).
5. Map GraphQL types into accurate Python annotations with correct nullability.
6. Generate typed Pydantic v2 models for every response shape.
7. Generate typed query and mutation client methods.
8. Handle custom scalars via config.
9. Handle interfaces and unions via discriminated union pattern.
10. Inject `__typename` automatically — users write clean `.graphql` files.
11. Produce compiler-style diagnostics that identify the problem, its location, and how to fix it.
12. Generate deterministic, formatted source code.
13. Produce packages that import cleanly and pass `ruff check`.
14. Include automated tests covering the compiler pipeline end-to-end.

---

## Definition of Done

The project is complete when this workflow succeeds:

```bash
nabu generate --config nabu.toml
```

And the generated package supports:

```python
from generated_client import Client

async with Client(url="https://example.com/graphql") as client:
    result = await client.get_student(id="123")
    print(result.student.id)
    print(result.student.status)
```

The package must:

- contain no syntax errors
- pass `ruff check --select F`
- correctly serialize operation variables (camelCase wire names)
- correctly deserialize GraphQL responses (camelCase → snake_case)
- resolve polymorphic responses to the correct concrete Pydantic model
- report clear errors for invalid schemas and operations
- regenerate consistently without manual modifications
- not touch files whose content has not changed

---

## Current State (as of Phase 11)

**All MVP requirements are met.** Both sample schemas generate clean, importable clients:

- `samples/university/` — 6 object types, 3 enums, 8 inputs, 14 operations including polymorphic search query
- `samples/euporie/` — 47 model classes, 13 enums, 20 inputs, 4 union aliases, 7 operations

Verified end-to-end against a live euporie SAP BTP instance:
- JWT auth via UAA clientid/clientsecret
- Pagination, camelCase aliases, datetime fields, discriminated union resolution

144 tests pass. `ruff check --select F` is clean on source and both generated samples.

---

## Classification

Nabu Forge is:

- A **compiler** in formal-language terms (parse → analyse → transform → generate)
- A **DSL compiler** (source language: GraphQL SDL + operations; target language: Python)
- A **source-code generator** from an engineering perspective
- A **model-to-text transformer** in model-driven engineering

It is not an interpreter — it does not execute the GraphQL schema. It analyses source definitions and generates another program.

`graphql-core` is the frontend parser only. The primary contribution of Nabu Forge lies in the semantic model, type translation rules, IR, diagnostics, and Python code-generation backend.
