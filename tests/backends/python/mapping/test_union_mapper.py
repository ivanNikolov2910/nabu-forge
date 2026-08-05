from nabu.backends.python.mapping.union_mapper import map_union


def test_basic_union():
    assert map_union(["Student", "Course"]) == "Student | Course"


def test_union_preserves_order():
    assert map_union(["Zebra", "Apple"]) == "Zebra | Apple"


def test_union_single_member():
    assert map_union(["Student"]) == "Student"


def test_union_applies_to_class_name():
    assert map_union(["student", "course"]) == "Student | Course"
