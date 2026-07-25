# Project Overview

**Nabu Forge** is a schema-driven compiler and code-generation tool that transforms GraphQL schemas and operation definitions into type-safe Python client packages.

The project uses `graphql-core` to parse and validate GraphQL Schema Definition Language, while the remaining compiler stages are implemented as part of Nabu Forge.

The final system should accept GraphQL SDL files and GraphQL operation documents as input and generate a complete Python package containing:

* typed input models;
* typed response models;
* enum definitions;
* custom scalar mappings;
* query and mutation methods;
* HTTP transport logic;
* serialization and deserialization logic;
* validation and diagnostic messages.

---

## Primary Goal

The main goal of Nabu Forge is to translate GraphQL definitions into usable Python source code.

The general transformation is:

```text
GraphQL SDL and operations
            ↓
       Nabu Forge
            ↓
Typed Python client package
```

The generated package should allow developers to work with a GraphQL API through typed Python methods rather than manually constructing GraphQL requests and processing raw dictionaries.

Example generated usage:

```python
client = Client(
    url="https://example.com/graphql",
    headers={"Authorization": "Bearer token"},
)

student = await client.get_student(student_id="123")

print(student.id)
print(student.status)
```
