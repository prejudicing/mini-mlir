cmake_minimum_required(VERSION 3.20)
project(MLIRPatternRewrite LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(MLIR REQUIRED CONFIG)

add_executable(mlir-pattern-rewrite main.cpp)
target_include_directories(mlir-pattern-rewrite SYSTEM PRIVATE
  ${MLIR_INCLUDE_DIRS}
  ${LLVM_INCLUDE_DIRS}
)
add_definitions(${LLVM_DEFINITIONS})
target_link_libraries(mlir-pattern-rewrite PRIVATE
  MLIRParser
  MLIRIR
  MLIRPass
  MLIRTransforms
  MLIRArithDialect
  MLIRFuncDialect
)

enable_testing()
add_test(NAME lab01-rewrite
  COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/tests/run.sh
    $<TARGET_FILE:mlir-pattern-rewrite>)
