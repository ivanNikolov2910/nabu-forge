# Development Plan

## Phase 1: Project foundation

Implement:

* repository structure;
* packaging;
* CLI entry point;
* configuration loading;
* basic diagnostics;
* GraphQL file loading.

Expected result:

```bash
nabu --version
nabu validate
```

---

## Phase 2: Parsing and schema loading

Implement:

* schema parsing through `graphql-core`;
* operation parsing;
* schema validation;
* AST traversal;
* schema inspection command.

Expected result:

```bash
nabu inspect --schema schema.graphqls
```

---

## Phase 3: Symbol table

Implement:

* symbol registration;
* type lookup;
* duplicate detection;
* interface implementation lookup;
* union member lookup;
* operation and fragment registration.

Expected result:

The complete GraphQL type system can be queried through an internal API.

---

## Phase 4: Intermediate representation

Implement:

* IR type definitions;
* AST-to-IR transformation;
* recursive GraphQL type references;
* operation IR;
* response-selection IR;
* source location preservation.

Expected result:

The GraphQL schema and operations are represented independently of `graphql-core`.

---

## Phase 5: Semantic analysis

Implement:

* type-reference validation;
* custom scalar validation;
* operation validation;
* fragment validation;
* naming validation;
* unsupported-feature diagnostics.

Expected result:

Invalid generation input fails before code generation.

---

## Phase 6: Python type mapping

Implement:

* built-in scalar mappings;
* custom scalar configuration;
* nullability conversion;
* list conversion;
* enum mapping;
* input-model mapping;
* interface and union mapping.

Expected result:

Every supported GraphQL type can be represented as a Python type annotation.

---

## Phase 7: Model generation

Generate:

* enums;
* input models;
* schema models;
* operation-specific response models;
* scalar helpers;
* package exports.

Expected result:

The generated models can be imported and validated independently.

---

## Phase 8: Client generation

Generate:

* asynchronous client methods;
* GraphQL request documents;
* variable serialization;
* response deserialization;
* GraphQL error handling;
* HTTP transport integration.

Expected result:

Generated methods can communicate with a GraphQL endpoint.

---

## Phase 9: Interfaces, unions, and fragments

Implement:

* inline fragments;
* named fragments;
* `__typename`;
* discriminated unions;
* interface implementation models;
* union member models.

Expected result:

Polymorphic GraphQL responses are parsed into precise Python types.

---

## Phase 10: Quality and validation

Add:

* unit tests;
* integration tests;
* snapshot tests;
* generated-code compilation tests;
* `mypy` or `pyright` checks;
* formatting checks;
* deterministic-output tests.

Expected result:

Generated packages are valid, stable, and statically checkable.
