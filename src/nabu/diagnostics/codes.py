from enum import StrEnum


class ErrorCode(StrEnum):
    # E001–E009: system errors (config, filesystem)
    CONFIG_NOT_FOUND = "E001"
    CONFIG_MISSING_FIELDS = "E002"
    SCHEMA_PATH_NOT_FOUND = "E003"
    OPERATIONS_PATH_NOT_FOUND = "E004"

    # E010–E019: schema/operation parsing and validation
    PARSER_SYNTAX_ERROR = "E010"
    PARSER_VALIDATION_ERROR = "E011"
    DUPLICATE_TYPE = "E012"
    DUPLICATE_OPERATION = "E013"
