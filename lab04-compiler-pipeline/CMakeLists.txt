cmake_minimum_required(VERSION 3.20)
project(Lab04 LANGUAGES CXX)
include(../cmake/MLIRLab.cmake)
add_subdirectory(../lab03-dialect-conversion toy-conversion EXCLUDE_FROM_ALL)

add_executable(compiler-opt tools/compiler-opt.cpp lib/Pipelines.cpp)
target_include_directories(compiler-opt PRIVATE include)
target_link_libraries(compiler-opt PRIVATE ToyConversion MLIROptLib
  MLIRTransforms MLIRArithToLLVM MLIRFuncToLLVM
  MLIRReconcileUnrealizedCasts MLIRLLVMDialect)
find_program(MLIR_TRANSLATE NAMES mlir-translate-20 mlir-translate
  HINTS "${LLVM_TOOLS_BINARY_DIR}" REQUIRED)
find_program(LLVM_LLI NAMES lli-20 lli HINTS "${LLVM_TOOLS_BINARY_DIR}" REQUIRED)
add_lab_lit_test(compiler-opt)
