from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VariableInfo:
    name:             str
    type_name:        str              = "UNKNOWN"
    declared:         bool             = False
    used:             bool             = False
    assigned:         bool             = False
    initialized:      bool             = False
    is_argument:      bool             = False
    is_array:         bool             = False
    declaration_node: Optional[object] = None


@dataclass
class ScopeInfo:
    name: str
    kind: str
    variables: dict[str, VariableInfo] = field(default_factory=dict)
    variable_order: list[str] = field(default_factory=list)


@dataclass
class ProcedureInfo:
    name: str
    kind: str
    arguments: list[str]
    node: object | None = None
    return_type: str | None = None


@dataclass
class SemanticInfo:
    scopes: list[ScopeInfo] = field(default_factory=list)
    procedures: dict[str, ProcedureInfo] = field(default_factory=dict)
