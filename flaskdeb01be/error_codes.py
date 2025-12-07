from enum import IntEnum

class ErrorCode(IntEnum):
    OK = 0,
    GENERIC_ERROR = 512,
    PARAMETER_ERROR = 513
