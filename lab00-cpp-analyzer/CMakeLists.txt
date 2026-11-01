cmake_minimum_required(VERSION 3.20)

project(MLIRAnalyzer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(MLIR REQUIRED CONFIG)

include_directories(
    ${MLIR_INCLUDE_DIRS}
    ${LLVM_INCLUDE_DIRS}
)

add_definitions(${LLVM_DEFINITIONS})

add_executable(mlir-analyzer
    main.cpp
)

target_link_libraries(mlir-analyzer
    PRIVATE
    MLIRParser
    MLIRIR
    MLIRPass
    MLIRArithDialect
    MLIRFuncDialect
)