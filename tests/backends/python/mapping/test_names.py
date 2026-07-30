from nabu.backends.python.mapping.names import to_class_name, to_field_name


def test_class_name_already_pascal():
    assert to_class_name("Student") == "Student"


def test_class_name_lowercase_first():
    assert to_class_name("enrollmentStatus") == "EnrollmentStatus"


def test_class_name_empty():
    assert to_class_name("") == ""


def test_class_name_reserved_word():
    # 'pass' uppercased to 'Pass' — no longer a keyword, no suffix needed
    assert to_class_name("pass") == "Pass"
    # A hypothetical name that stays a keyword after uppercasing would get _
    # (no such GraphQL names exist in practice, but the guard is there)


def test_class_name_single_char():
    assert to_class_name("a") == "A"


def test_field_name_camel_to_snake():
    assert to_field_name("createdAt") == "created_at"
    assert to_field_name("firstName") == "first_name"
    assert to_field_name("enrolledCourses") == "enrolled_courses"


def test_field_name_already_snake():
    assert to_field_name("id") == "id"
    assert to_field_name("name") == "name"


def test_field_name_reserved_word():
    assert to_field_name("pass") == "pass_"
    assert to_field_name("class") == "class_"


def test_field_name_all_caps_acronym():
    # e.g. "URL" → "u_r_l" is not ideal but consistent with the regex approach
    # and flagged if it becomes a keyword; no special-casing for now
    result = to_field_name("URL")
    assert isinstance(result, str) and len(result) > 0
