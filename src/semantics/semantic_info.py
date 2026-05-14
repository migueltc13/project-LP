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
    name:           str
    kind:           str
    variables:      dict[str, VariableInfo] = field(default_factory=dict)
    variable_order: list[str]               = field(default_factory=list)


@dataclass
class ProcedureInfo:
    name:        str
    kind:        str
    arguments:   list[str]
    node:        Optional[object] = None
    return_type: Optional[str]    = None


@dataclass
class SemanticInfo:
    scopes:           list[ScopeInfo]          = field(default_factory=list)
    procedures:       dict[str, ProcedureInfo] = field(default_factory=dict)
    expression_types: dict[int, str]           = field(default_factory=dict)


def print_semantic_info(
    semantic_info: SemanticInfo,
    show_intrinsics: bool = False
):
    print("Semantic Information:")
    print("=====================")

    print("\nProcedures:")

    procedures = {
        proc_name: proc_info
        for proc_name, proc_info in semantic_info.procedures.items()
        if show_intrinsics or not proc_info.kind.startswith("intrinsic")
    }

    if procedures:
        for proc_name, proc_info in procedures.items():
            print(f"  {proc_name} ({proc_info.kind})")

            if proc_info.arguments:
                print(f"    Arguments: {', '.join(proc_info.arguments)}")
            else:
                print("    Arguments: None")

            if proc_info.return_type:
                print(f"    Return Type: {proc_info.return_type}")
            else:
                print("    Return Type: None")
    else:
        print("  None")

    print("\nScopes:")

    for scope in semantic_info.scopes:
        print(f"  Scope: {scope.name} ({scope.kind})")

        if scope.variables:
            print("    Variables:")

            for var_name in scope.variable_order:
                var_info = scope.variables[var_name]

                status = []

                if var_info.declared:
                    status.append("declared")
                if var_info.used:
                    status.append("used")
                if var_info.assigned:
                    status.append("assigned")
                if var_info.initialized:
                    status.append("initialized")
                if var_info.is_argument:
                    status.append("argument")
                if var_info.is_array:
                    status.append("array")

                status_str = ", ".join(status) if status else "none"

                print(f"      {var_name} ({var_info.type_name}): {status_str}")
        else:
            print("    Variables: None")
