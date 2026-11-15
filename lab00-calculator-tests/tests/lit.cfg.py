import os
import shlex
import lit.formats

# config 由 lit 提供；上一步 site 配置已经填好了工具路径。
config.name = "Lab00-Calculator"
config.test_format = lit.formats.ShTest(True)
config.suffixes = [".test"]
config.test_source_root = os.path.dirname(__file__)
config.substitutions += [
    ("%calculator", shlex.quote(config.calculator)),
    ("%FileCheck", shlex.quote(config.filecheck)),
    ("%python", shlex.quote(config.python)),
]
# %s（当前测试文件）、%S（该文件所在目录）是 lit 内置替换。
