import os
import shlex
import lit.formats
config.name = "Lab03"
config.test_format = lit.formats.ShTest(True)
config.suffixes = [".mlir"]
config.test_source_root = os.path.dirname(__file__)
config.substitutions += [
    ("%toy-opt", shlex.quote(os.path.join(config.tool_dir, "toy-convert-opt"))),
    ("%FileCheck", shlex.quote(config.filecheck)),
]
