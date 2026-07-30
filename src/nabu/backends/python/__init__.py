# Language backend: Python
#
# This package owns everything Python-specific in the compiler pipeline:
#
#   mapping/    — Phase 6: TypeRef -> Python annotation string, import tracking
#   codegen/    — Phase 7: model/enum/input/operation file generation
#   client/     — Phase 8: async client, transport, serialisation
