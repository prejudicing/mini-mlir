# Lab0：普通 C++ 计算器的测试工程

文件结构与职责：[PNG 图](diagrams/file-structure.png) · [可缩放 SVG](diagrams/file-structure.svg)。

通过一个整数计算器，学习 CMake → CTest → lit → FileCheck。无需 MLIR 开发库；需要 C++17 编译器、CMake 3.20+、Ninja、Python3、lit 和 FileCheck。沿用现有 LLVM 20 环境即可，不需要额外 pip 安装。

逐步学习见 [TUTORIAL.md](TUTORIAL.md)，其中[第 9 节逐条解释 CMake 语法与参数](TUTORIAL.md#9-cmakeliststxt-逐条语法讲解)。从项目根目录快速验证：

```bash
bash scripts/build-and-test.sh lab00-calculator-tests
```

也可以独立构建：

```bash
cd ~/projects/mlir-learning/lab00-calculator-tests
cmake -S . -B build -G Ninja
cmake --build build
./build/bin/calculator add 3 5
ctest --test-dir build --output-on-failure
```

程序支持 `add/sub/mul/div`，操作数范围 ±1000000000，整数除法向零截断；成功退出码为 0，错误退出码为 2。CTest 报告 1 个测试组，lit 报告 4 个测试文件，其中共有 17 条 RUN 命令。

| 文件 | 用途 |
| --- | --- |
| main.cpp | 计算器，不使用 LLVM/MLIR API |
| CMakeLists.txt | 构建、发现工具、生成配置、登记测试 |
| tests/lit.site.cfg.py.in | CMake 填写绝对路径的配置模板 |
| tests/lit.cfg.py | lit 测试发现与命令替换规则 |
| tests/*.test | 测试命令和预期输出 |
| tests/check_error.py | 验证失败退出码及空标准输出，将错误文本交给 FileCheck |
| build/tests/lit.site.cfg.py | 自动生成的实际配置 |

其他安装路径可以通过 `-DLLVM_TOOLS_ROOT=/path/to/llvm` 指定；也可显式设置 `-DLIT_EXECUTABLE=/path/to/lit.py -DFILECHECK_EXECUTABLE=/path/to/FileCheck`。路径变化后重新运行 CMake。
