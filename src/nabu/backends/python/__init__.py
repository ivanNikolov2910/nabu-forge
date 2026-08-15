# Language backend: Python
#
# This package owns everything Python-specific in the compiler pipeline:
#
#   mapping/    - TypeRef -> Python annotation string, import tracking
#   codegen/    - model/enum/input/operation file generation
#   client/     - async client, transport, serialisation
