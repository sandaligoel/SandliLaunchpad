"""Shared IO field types for agent contracts."""

from __future__ import annotations

from enum import Enum


class IOFieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    FILE = "file"
    UNKNOWN = "unknown"
