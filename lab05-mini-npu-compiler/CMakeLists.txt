cmake_minimum_required(VERSION 3.20)
project(Lab05 LANGUAGES CXX)
include(../cmake/MLIRLab.cmake)
include_directories(include ${CMAKE_CURRENT_BINARY_DIR})

# TableGen 读取 .td，分别生成方言/操作的声明与实现；C++ 再通过 #include 使用。
set(LLVM_TARGET_DEFINITIONS include/NPU/NPU.td)
mlir_tablegen(NPUDialect.h.inc -gen-dialect-decls -dialect=npu)
mlir_tablegen(NPUDialect.cpp.inc -gen-dialect-defs -dialect=npu)
mlir_tablegen(NPUOps.h.inc -gen-op-decls)
mlir_tablegen(NPUOps.cpp.inc -gen-op-defs)
add_public_tablegen_target(NPUIncGen)

# 三个实现组成可复用后端库：方言与验证、变换 Pass、指令发射。
add_library(NPUCompiler lib/NPUDialect.cpp lib/Passes.cpp lib/Emitter.cpp)
# 先生成 .inc，再编译包含它们的 C++ 源文件，避免并行构建时缺文件。
add_dependencies(NPUCompiler NPUIncGen)
target_include_directories(NPUCompiler PUBLIC include ${CMAKE_CURRENT_BINARY_DIR})
target_link_libraries(NPUCompiler PUBLIC MLIRIR MLIRPass MLIRTransforms
  MLIRLinalgDialect MLIRFuncDialect MLIRArithDialect)
# 两个独立入口复用同一后端：opt 输出 IR，translate 输出伪指令。
add_executable(npu-opt tools/npu-opt.cpp)
add_dependencies(npu-opt NPUIncGen)
target_link_libraries(npu-opt PRIVATE NPUCompiler MLIROptLib)
add_executable(npu-translate tools/npu-translate.cpp)
add_dependencies(npu-translate NPUIncGen)
target_link_libraries(npu-translate PRIVATE NPUCompiler MLIRParser)
# lit/FileCheck 检查 IR/诊断/指令文本，Python 测试检查实际数值。
add_lab_lit_test(npu-opt)
add_dependencies(check-npu-opt npu-translate)
add_test(NAME NPU-numerical
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/numerical.py
    $<TARGET_FILE:npu-opt> $<TARGET_FILE:npu-translate>)
add_test(NAME NPU-int8
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/int8_numerical.py
    $<TARGET_FILE:npu-opt> $<TARGET_FILE:npu-translate>)
