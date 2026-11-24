cmake_minimum_required(VERSION 3.20)
# 本目录只有 Python 前端与编排，因此不直接启用 C++；C++ 后端由 Lab5 构建。
project(Lab06 LANGUAGES NONE)
include(CTest)

# Python dependencies stay in this lab's ignored build directory.
if(NOT DEFINED Python3_EXECUTABLE AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/build/venv/bin/python")
  set(Python3_EXECUTABLE "${CMAKE_CURRENT_SOURCE_DIR}/build/venv/bin/python")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
# 配置时先检查运行依赖，避免到测试阶段才发现解释器缺少 torch/numpy。
execute_process(COMMAND "${Python3_EXECUTABLE}" -c "import torch, numpy"
  RESULT_VARIABLE torch_status OUTPUT_QUIET ERROR_QUIET)
if(NOT torch_status EQUAL 0)
  message(FATAL_ERROR "Run bash lab06-pytorch-to-npu/scripts/setup.sh first, or set Python3_EXECUTABLE to a PyTorch environment")
endif()

# Reuse the actual Lab5 source and binaries, not a copied backend.
set(LAB5_BUILD_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../lab05-mini-npu-compiler/build"
  CACHE PATH "Build directory of the reused Lab5 backend")
get_filename_component(LAB5_BUILD_DIR "${LAB5_BUILD_DIR}" ABSOLUTE)
# ALL 表示默认构建就准备后端；这里运行真实的 Lab5 CMake 工程，而非复制二进制。
add_custom_target(lab6-backend ALL
  COMMAND "${CMAKE_COMMAND}" -S "${CMAKE_CURRENT_SOURCE_DIR}/../lab05-mini-npu-compiler"
    -B "${LAB5_BUILD_DIR}" -G Ninja "-DMLIR_DIR=${MLIR_DIR}" "-DLLVM_DIR=${LLVM_DIR}"
  COMMAND "${CMAKE_COMMAND}" --build "${LAB5_BUILD_DIR}" --target npu-opt npu-translate --parallel 2
  USES_TERMINAL)
if(BUILD_TESTING)
  # CTest 启动 Python unittest；测试中调用编译器并执行模拟器，做端到端数值验证。
  add_test(NAME pytorch-npu-tests
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/run.py"
      --backend-dir "${LAB5_BUILD_DIR}" --output-dir "${CMAKE_CURRENT_BINARY_DIR}/tests")
endif()
