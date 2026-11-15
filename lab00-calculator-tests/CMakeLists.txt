cmake_minimum_required(VERSION 3.20)
project(Lab00CalculatorTests LANGUAGES CXX)

# 只使用 C++ 标准库，不查找、不链接 MLIR 库。
add_executable(calculator main.cpp)
target_compile_features(calculator PRIVATE cxx_std_17)
# 为本实验统一可执行程序目录，包括使用多配置生成器的情况。
set_target_properties(calculator PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/bin/$<0:>")

find_package(Python3 REQUIRED COMPONENTS Interpreter)
# CACHE 变量允许用户通过 -D 指定其他 LLVM 安装位置。
set(LLVM_TOOLS_ROOT "/usr/lib/llvm-20" CACHE PATH "LLVM tools installation")
find_program(FILECHECK_EXECUTABLE NAMES FileCheck-20 FileCheck
  HINTS "${LLVM_TOOLS_ROOT}/bin" REQUIRED)
find_program(LIT_EXECUTABLE NAMES llvm-lit lit lit.py
  HINTS "${LLVM_TOOLS_ROOT}/build/utils/lit" "${LLVM_TOOLS_ROOT}/bin" REQUIRED)

# @ONLY：只替换模板中的 @变量名@，保留其他 Python 文本。
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/tests")
configure_file(tests/lit.site.cfg.py.in tests/lit.site.cfg.py @ONLY)

# enable_testing 开启测试登记，add_test 记录命令，此处不运行测试。
enable_testing()
add_test(NAME Lab00-calculator-lit
  COMMAND "${Python3_EXECUTABLE}" "${LIT_EXECUTABLE}" -sv
          "${CMAKE_CURRENT_BINARY_DIR}/tests")
