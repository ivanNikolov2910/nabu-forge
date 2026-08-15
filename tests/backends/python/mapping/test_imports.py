from nabu.backends.python.mapping.imports import ImportCollector


def test_bare_import_for_datetime():
    c = ImportCollector()
    c.add("datetime.datetime")
    assert "import datetime" in c.render()


def test_from_import_for_typing():
    c = ImportCollector()
    c.add("typing.Any")
    assert "from typing import Any" in c.render()


def test_primitives_need_no_import():
    c = ImportCollector()
    for ann in ("str", "int", "float", "bool", "None", "list[str]", "str | None"):
        c.add(ann)
    assert c.render() == ""


def test_deduplication():
    c = ImportCollector()
    c.add("datetime.datetime")
    c.add("datetime.datetime")
    assert c.render().count("import datetime") == 1


def test_relative_import():
    c = ImportCollector()
    c.add_relative("enums", "EnrollmentStatus")
    assert "from .enums import EnrollmentStatus" in c.render()


def test_multiple_from_same_module():
    c = ImportCollector()
    c.add("typing.Any")
    c.add("typing.Optional")
    rendered = c.render()
    assert "from typing import" in rendered
    assert "Any" in rendered
    assert "Optional" in rendered


def test_render_order_stdlib_before_relative():
    c = ImportCollector()
    c.add("datetime.datetime")
    c.add_relative("enums", "Status")
    rendered = c.render()
    assert rendered.index("import datetime") < rendered.index("from .enums")


def test_render_stable():
    c = ImportCollector()
    c.add("datetime.datetime")
    c.add("typing.Any")
    c.add_relative("enums", "Status")
    assert c.render() == c.render()
