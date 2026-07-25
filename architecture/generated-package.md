# Generated Python Package

## Generated Models

Example GraphQL type:

```graphql
type Student {
    id: ID!
    status: EnrollmentStatus!
    description: String
}
```

Possible generated Python model:

```python
from pydantic import BaseModel


class Student(BaseModel):
    id: str
    status: EnrollmentStatus
    description: str | None = None
```

---

## Generated Enums

Example GraphQL enum:

```graphql
enum EnrollmentStatus {
    ENROLLED
    ACTIVE
    GRADUATED
    WITHDRAWN
}
```

Generated Python:

```python
from enum import Enum


class EnrollmentStatus(str, Enum):
    ENROLLED = "ENROLLED"
    ACTIVE = "ACTIVE"
    GRADUATED = "GRADUATED"
    WITHDRAWN = "WITHDRAWN"
```

---

## Generated Input Models

Example GraphQL input:

```graphql
input CreateStudentInput {
    name: String!
    description: String
}
```

Generated Python:

```python
from pydantic import BaseModel


class CreateStudentInput(BaseModel):
    name: str
    description: str | None = None
```

---

## Generated Client Methods

Example GraphQL operation:

```graphql
query GetStudent($id: ID!) {
    student(id: $id) {
        id
        status
        description
    }
}
```

Possible generated client method:

```python
async def get_student(self, id: str) -> GetStudentResult:
    response = await self._transport.execute(
        query=GET_STUDENT_DOCUMENT,
        variables={"id": id},
    )

    return GetStudentResult.model_validate(response)
```

---

## Schema Models and Operation Models

Nabu Forge should distinguish between schema models and operation-specific response models.

A schema type describes every field that may be requested:

```graphql
type Student {
    id: ID!
    status: EnrollmentStatus!
    description: String
    metadata: StudentMetadata
}
```

An operation may select only part of that type:

```graphql
query GetStudent($id: ID!) {
    student(id: $id) {
        id
        status
    }
}
```

The generated response model should represent the selected fields:

```python
class GetStudentStudent(BaseModel):
    id: str
    status: EnrollmentStatus
```

It should not assume that unselected fields are present in the response.

This distinction is necessary for accurate static typing.

---

## Interfaces and Unions

Interfaces and unions require special handling.

Example:

```graphql
interface Student {
    id: ID!
}

type UndergraduateStudent implements Student {
    id: ID!
    major: String!
}

type GraduateStudent implements Student {
    id: ID!
    thesisTitle: String!
}
```

The operation should request `__typename`:

```graphql
query GetStudent($id: ID!) {
    student(id: $id) {
        __typename
        id

        ... on UndergraduateStudent {
            major
        }

        ... on GraduateStudent {
            thesisTitle
        }
    }
}
```

Possible generated Python representation:

```python
StudentResult = UndergraduateStudentResult | GraduateStudentResult
```

A discriminated union may be used for response parsing.

---

## Naming and Alias Handling

GraphQL field names may conflict with Python keywords.

Example:

```graphql
type ImportDefinition {
    from: String!
    class: String!
}
```

Generated Python cannot use these names directly.

A valid model may be:

```python
from pydantic import BaseModel, Field


class ImportDefinition(BaseModel):
    from_: str = Field(alias="from")
    class_: str = Field(alias="class")
```

The naming subsystem should handle:

* Python keywords;
* invalid Python identifiers;
* snake-case conversion;
* class-name conversion;
* duplicate generated names;
* GraphQL aliases;
* module-name conflicts.
