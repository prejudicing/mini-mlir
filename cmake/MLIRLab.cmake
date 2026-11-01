set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
find_package(MLIR REQUIRED CONFIG)
list(APPEND CMAKE_MODULE_PATH "${MLIR_CMAKE_DIR}" "${LLVM_CMAKE_DIR}")
include(TableGen)
include(AddLLVM)
include(AddMLIR)
enable_testing()
include_directories(SYSTEM ${MLIR_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS})
add_definitions(${LLVM_DEFINITIONS})

# Ubuntu 的 lit 随 LLVM 源码工具安装，不要求 pip 或系统 PATH 中存在 lit。
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_program(FILECHECK_EXECUTABLE NAMES FileCheck-20 FileCheck
  HINTS "${LLVM_TOOLS_BINARY_DIR}" REQUIRED)
find_file(LLVM_LIT_SCRIPT lit.py
  HINTS "${LLVM_TOOLS_BINARY_DIR}/../build/utils/lit"
        "/usr/lib/llvm-20/build/utils/lit" REQUIRED)

function(add_lab_lit_test tool)
  configure_file(${PROJECT_SOURCE_DIR}/tests/lit.site.cfg.py.in
    ${PROJECT_BINARY_DIR}/tests/lit.site.cfg.py @ONLY)
  add_test(NAME ${PROJECT_NAME}-lit
    COMMAND ${Python3_EXECUTABLE} ${LLVM_LIT_SCRIPT} -v
      ${PROJECT_BINARY_DIR}/tests)
  add_custom_target(check-${tool}
    COMMAND ${Python3_EXECUTABLE} ${LLVM_LIT_SCRIPT} -v
      ${PROJECT_BINARY_DIR}/tests DEPENDS ${tool} USES_TERMINAL)
endfunction()
