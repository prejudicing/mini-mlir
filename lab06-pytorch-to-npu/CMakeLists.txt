cmake_minimum_required(VERSION 3.20)
project(Lab06 LANGUAGES NONE)
include(CTest)

# Python dependencies stay in this lab's ignored build directory.
if(NOT DEFINED Python3_EXECUTABLE AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/build/venv/bin/python")
  set(Python3_EXECUTABLE "${CMAKE_CURRENT_SOURCE_DIR}/build/venv/bin/python")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
execute_process(COMMAND "${Python3_EXECUTABLE}" -c "import torch, numpy"
  RESULT_VARIABLE torch_status OUTPUT_QUIET ERROR_QUIET)
if(NOT torch_status EQUAL 0)
  message(FATAL_ERROR "Run bash lab06-pytorch-to-npu/scripts/setup.sh first, or set Python3_EXECUTABLE to a PyTorch environment")
endif()

# Reuse the actual Lab5 source and binaries, not a copied backend.
set(LAB5_BUILD_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../lab05-mini-npu-compiler/build"
  CACHE PATH "Build directory of the reused Lab5 backend")
get_filename_component(LAB5_BUILD_DIR "${LAB5_BUILD_DIR}" ABSOLUTE)
add_custom_target(lab6-backend ALL
  COMMAND "${CMAKE_COMMAND}" -S "${CMAKE_CURRENT_SOURCE_DIR}/../lab05-mini-npu-compiler"
    -B "${LAB5_BUILD_DIR}" -G Ninja "-DMLIR_DIR=${MLIR_DIR}" "-DLLVM_DIR=${LLVM_DIR}"
  COMMAND "${CMAKE_COMMAND}" --build "${LAB5_BUILD_DIR}" --target npu-opt npu-translate --parallel 2
  USES_TERMINAL)
if(BUILD_TESTING)
  add_test(NAME pytorch-npu-tests
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/run.py"
      --backend-dir "${LAB5_BUILD_DIR}" --output-dir "${CMAKE_CURRENT_BINARY_DIR}/tests")
endif()
