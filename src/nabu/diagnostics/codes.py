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

    # E020-E029: semantic analysis errors
    UNKNOWN_TYPE_REF = "E020"
    UNMAPPED_SCALAR = "E021"
    UNKNOWN_VARIABLE_TYPE = "E022"
    UNKNOWN_FIELD = "E023"
    UNKNOWN_FRAGMENT = "E024"
    BAD_FRAGMENT_TARGET = "E025"
    NAME_COLLISION = "E026"
    RESERVED_NAME = "E027"
    UNSUPPORTED_FEATURE = "E028"
