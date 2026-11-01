cmake_minimum_required(VERSION 3.20)
project(ToyDialectLab LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(MLIR REQUIRED CONFIG)
list(APPEND CMAKE_MODULE_PATH "${MLIR_CMAKE_DIR}" "${LLVM_CMAKE_DIR}")
include(TableGen)
include(AddLLVM)
include(AddMLIR)

include_directories(SYSTEM ${MLIR_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR})
add_definitions(${LLVM_DEFINITIONS})

# .td 是手写输入，.inc 是构建时生成的 C++，不应直接修改。
set(LLVM_TARGET_DEFINITIONS include/Toy/ToyDialect.td)
mlir_tablegen(ToyDialect.h.inc -gen-dialect-decls -dialect=toy)
mlir_tablegen(ToyDialect.cpp.inc -gen-dialect-defs -dialect=toy)
add_public_tablegen_target(ToyDialectIncGen)

set(LLVM_TARGET_DEFINITIONS include/Toy/ToyOps.td)
mlir_tablegen(ToyOps.h.inc -gen-op-decls)
mlir_tablegen(ToyOps.cpp.inc -gen-op-defs)
add_public_tablegen_target(ToyOpsIncGen)

add_library(ToyDialect lib/ToyDialect.cpp lib/ToyOps.cpp)
target_include_directories(ToyDialect PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR})
target_include_directories(ToyDialect SYSTEM PUBLIC ${MLIR_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS})
add_dependencies(ToyDialect ToyDialectIncGen ToyOpsIncGen)
target_link_libraries(ToyDialect PUBLIC
  MLIRIR MLIRSideEffectInterfaces MLIRInferTypeOpInterface)

add_executable(toy-opt tools/toy-opt.cpp)
add_dependencies(toy-opt ToyDialectIncGen ToyOpsIncGen)
target_link_libraries(toy-opt PRIVATE ToyDialect MLIROptLib MLIRFuncDialect)

add_executable(toy-build tools/toy-build.cpp)
add_dependencies(toy-build ToyDialectIncGen ToyOpsIncGen)
target_link_libraries(toy-build PRIVATE ToyDialect MLIRFuncDialect)

include(CTest)
if(BUILD_TESTING AND CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  find_program(FILECHECK_EXECUTABLE NAMES FileCheck-20 FileCheck
    HINTS "${LLVM_TOOLS_BINARY_DIR}" REQUIRED)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_test(NAME toy-dialect-tests
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/run.py
      $<TARGET_FILE:toy-opt> ${FILECHECK_EXECUTABLE} $<TARGET_FILE:toy-build>)
endif()
