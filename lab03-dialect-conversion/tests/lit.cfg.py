# 提供文件路径处理功能。
import os

# 提供 Shell 参数转义功能，避免路径中的空格等字符影响命令执行。
import shlex

# 引入 LLVM 的 lit 测试格式。
import lit.formats

# 设置这组测试的名称，测试报告中会显示 Lab03。
# config 由 lit 提供，不需要在这里创建。
config.name = "Lab03"

# 使用 Shell 命令测试格式。
# True 表示通过外部 Shell 执行测试文件中的 RUN 指令。
config.test_format = lit.formats.ShTest(True)

# 只把后缀为 .mlir 的文件识别为测试文件。
config.suffixes = [".mlir"]

# 将当前配置文件所在目录设为测试源码根目录。
# __file__ 是当前 Python 文件的路径，dirname() 取它所在的目录。
config.test_source_root = os.path.dirname(__file__)

# 向已有的命令替换规则列表中追加规则。
# lit 执行 RUN 指令前，会将下面的占位符替换为实际工具路径。
# config.tool_dir 和 config.filecheck 由其他配置文件预先设置。
config.substitutions += [
    (
        # 例如：将 RUN 指令中的 %toy-opt
        # 替换为 build/toy-convert-opt 的实际路径。
        "%toy-opt",
        shlex.quote(os.path.join(config.tool_dir, "toy-convert-opt")),
    ),
    (
        # 将 %FileCheck 替换为 FileCheck 工具的实际路径。
        "%FileCheck",
        shlex.quote(config.filecheck),
    ),
]