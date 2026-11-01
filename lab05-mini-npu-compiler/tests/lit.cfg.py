import os
import shlex
import lit.formats
config.name = "Lab05"
config.test_format = lit.formats.ShTest(True)
config.suffixes = [".mlir"]
config.test_source_root = os.path.dirname(__file__)
config.substitutions += [
    ("%npu-opt", shlex.quote(os.path.join(config.tool_dir, "npu-opt"))),
    ("%npu-translate", shlex.quote(os.path.join(config.tool_dir, "npu-translate"))),
    ("%FileCheck", shlex.quote(config.filecheck)),
    ("%python", shlex.quote(config.python)),
]
