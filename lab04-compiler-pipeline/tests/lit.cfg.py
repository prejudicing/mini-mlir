import os
import shlex
import lit.formats
config.name = "Lab04"
config.test_format = lit.formats.ShTest(True)
config.suffixes = [".mlir"]
config.test_source_root = os.path.dirname(__file__)
config.substitutions += [
    ("%compiler-opt", shlex.quote(os.path.join(config.tool_dir, "compiler-opt"))),
    ("%FileCheck", shlex.quote(config.filecheck)),
    ("%translate", shlex.quote(config.translate)),
    ("%lli", shlex.quote(config.lli)),
    ("%python", shlex.quote(config.python)),
]
