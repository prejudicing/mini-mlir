cmake_minimum_required(VERSION 3.20)
project(Lab05 LANGUAGES CXX)
include(../cmake/MLIRLab.cmake)
include_directories(include ${CMAKE_CURRENT_BINARY_DIR})

set(LLVM_TARGET_DEFINITIONS include/NPU/NPU.td)
mlir_tablegen(NPUDialect.h.inc -gen-dialect-decls -dialect=npu)
mlir_tablegen(NPUDialect.cpp.inc -gen-dialect-defs -dialect=npu)
mlir_tablegen(NPUOps.h.inc -gen-op-decls)
mlir_tablegen(NPUOps.cpp.inc -gen-op-defs)
add_public_tablegen_target(NPUIncGen)

add_library(NPUCompiler lib/NPUDialect.cpp lib/Passes.cpp lib/Emitter.cpp)
add_dependencies(NPUCompiler NPUIncGen)
target_include_directories(NPUCompiler PUBLIC include ${CMAKE_CURRENT_BINARY_DIR})
target_link_libraries(NPUCompiler PUBLIC MLIRIR MLIRPass MLIRTransforms
  MLIRLinalgDialect MLIRFuncDialect MLIRArithDialect)
add_executable(npu-opt tools/npu-opt.cpp)
add_dependencies(npu-opt NPUIncGen)
target_link_libraries(npu-opt PRIVATE NPUCompiler MLIROptLib)
add_executable(npu-translate tools/npu-translate.cpp)
add_dependencies(npu-translate NPUIncGen)
target_link_libraries(npu-translate PRIVATE NPUCompiler MLIRParser)
add_lab_lit_test(npu-opt)
add_dependencies(check-npu-opt npu-translate)
add_test(NAME NPU-numerical
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/numerical.py
    $<TARGET_FILE:npu-opt> $<TARGET_FILE:npu-translate>)
add_test(NAME NPU-int8
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/int8_numerical.py
    $<TARGET_FILE:npu-opt> $<TARGET_FILE:npu-translate>)
