import keyword
import re


def to_class_name(name: str) -> str:
    if not name:
        return name
    result = name[0].upper() + name[1:]
    return result + "_" if keyword.iskeyword(result) else result


def to_field_name(name: str) -> str:
    snake = re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")
    return snake + "_" if keyword.iskeyword(snake) else snake
