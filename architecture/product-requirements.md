# Product Requirements

## Minimum Viable Product

The first useful version should support:

* GraphQL SDL parsing through `graphql-core`;
* GraphQL operation documents;
* object types;
* input types;
* enums;
* built-in scalars;
* configurable custom scalars;
* lists and nullability;
* queries;
* mutations;
* Pydantic models;
* asynchronous HTTP requests;
* operation-specific response models;
* basic diagnostics;
* generated package exports.

The MVP may initially exclude:

* subscriptions;
* federation;
* file uploads;
* schema extensions;
* custom executable directives;
* persisted queries;
* automatic selection-set generation;
* synchronous clients;
* multiple target languages.

---

## Final Product Requirements

The final version of Nabu Forge should:

1. Parse GraphQL SDL and operation documents.
2. Validate the schema and operations.
3. Build a complete symbol table.
4. Perform project-specific semantic analysis.
5. Transform GraphQL definitions into a custom IR.
6. Map GraphQL types into accurate Python types.
7. Generate typed Python models.
8. Generate typed query and mutation methods.
9. Handle custom scalars.
10. Handle interfaces and unions.
11. Produce compiler-style diagnostics.
12. Generate deterministic and formatted source code.
13. Produce packages that pass Python compilation.
14. Produce packages that pass static type checking.
15. Include automated tests for the generated output.

---

## Definition of Done

The project can be considered complete when the following workflow succeeds:

```bash
nabu generate \
    --schema schema.graphqls \
    --operations operations/ \
    --output generated_client/
```

The generated package should then support:

```python
from generated_client import Client

client = Client(url="https://example.com/graphql")

result = await client.get_student(id="123")

print(result.student.id)
```

The package should:

* contain no syntax errors;
* pass formatting checks;
* pass static type checking;
* correctly serialize operation variables;
* correctly deserialize GraphQL responses;
* expose clear Python APIs;
* report useful errors for invalid schemas and operations;
* regenerate consistently without manual modifications.

---

## Classification of the Project

Nabu Forge can be described as:

> A schema-driven, source-generating DSL compiler that translates GraphQL SDL and GraphQL operations into type-safe Python client packages.

It is:

* a translator in the broadest sense;
* a compiler in formal-language terms;
* a DSL compiler more specifically;
* a source-code generator from an engineering perspective;
* a model-to-text transformer in model-driven engineering.

It is not primarily an interpreter because it does not execute the GraphQL schema directly. It analyses the source definitions and generates another program.

---

## Final Statement

`graphql-core` is sufficient for parsing and validating GraphQL SDL, but it is not sufficient for generating a complete Python client.

Nabu Forge must still implement:

* symbol resolution;
* semantic analysis;
* intermediate representation;
* GraphQL-to-Python type translation;
* operation analysis;
* response-model construction;
* client-method generation;
* transport integration;
* diagnostics;
* generated-package architecture.

The parser is therefore one reusable frontend component within a larger compiler system. The primary contribution of Nabu Forge lies in the semantic model, translation rules, intermediate representation, diagnostics, and Python code-generation backend.
