# CMake 基本语法：
#   命令名(参数1 参数2 ...)：用空白或换行分隔参数，不需要 C++ 的分号。
#   # 后面是注释；set(变量名 值) 设置变量；${变量名} 读取变量。
#   "${变量名}" 通常将展开结果作为一个参数；不加引号的展开可传入列表中的多个项。
#   PUBLIC、PRIVATE、REQUIRED 等词是对应命令识别的关键字，不是 C++ 访问修饰符。

# VERSION 是本命令的关键字；要求运行本项目的 CMake 至少为 3.20。
cmake_minimum_required(VERSION 3.20)
# project(项目名 LANGUAGES 语言列表)：声明项目并启用相应语言工具链。
# CXX 是 CMake 表示 C++ 的名称；项目名不要求与可执行文件名相同。
project(ToyDialectLab LANGUAGES CXX)

# set(变量名 值)：这里设置后续创建的 C++ 目标默认使用 C++17。
set(CMAKE_CXX_STANDARD 17)
# ON 表示启用；要求满足所请求的标准，不允许退回更旧的标准。
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# 让 Ninja/Makefile 等支持它的生成器输出 compile_commands.json，供 clangd 等工具使用。
# 该文件记录实际编译命令，不是程序运行时读取的配置。
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# find_package(包名 REQUIRED CONFIG)：按配置文件模式查找已安装的 MLIR。
# REQUIRED：找不到就终止配置；CONFIG：读取 MLIRConfig.cmake 等包配置文件。
# 配置时传入 -DMLIR_DIR=... 可指定其所在目录。
# 包配置会提供 MLIR_INCLUDE_DIRS、MLIR_CMAKE_DIR 和 MLIRIR 等库目标。
find_package(MLIR REQUIRED CONFIG)
# list(APPEND 列表变量 内容...)：向列表末尾追加元素。
# CMAKE_MODULE_PATH 是查找 CMake 辅助模块的目录列表，不是 C++ 头文件搜索路径。
list(APPEND CMAKE_MODULE_PATH "${MLIR_CMAKE_DIR}" "${LLVM_CMAKE_DIR}")
# include(模块名)：加载 .cmake 脚本，获得它定义的函数和宏。
# 与 C++ 的 #include 不同；这些模块帮助配置 TableGen 和 LLVM/MLIR 构建规则。
include(TableGen)
include(AddLLVM)
include(AddMLIR)

# include_directories([SYSTEM] 目录...)：设置当前目录作用域的头文件搜索路径。
# SYSTEM 把第三方目录作为系统头文件目录处理，通常减少其中产生的警告。
include_directories(SYSTEM ${MLIR_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS})
# CURRENT_SOURCE_DIR：当前 CMakeLists.txt 所在源码目录。
# CURRENT_BINARY_DIR：与当前源码目录对应的构建目录；独立构建时通常是本 Lab 的 build/。
# include/ 放手写头文件，构建目录放生成的 .inc，两者都需要能被 #include 找到。
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR})
# 传入 LLVM 提供的编译定义等选项，例如 -D开头的宏定义；不是包含或链接 LLVM 库。
add_definitions(${LLVM_DEFINITIONS})

# 以下命令来自前面加载的辅助模块，不是 CMake 最基础的内置命令。
# 它们在配置时登记生成规则，实际由 Ninja 等在构建时运行 TableGen。
# .td 是手写输入，.inc 是生成的 C++ 片段，不应直接修改。

# LLVM_TARGET_DEFINITIONS 是辅助函数约定读取的变量：指定接下来的 .td 输入文件。
set(LLVM_TARGET_DEFINITIONS include/Toy/ToyDialect.td)
# mlir_tablegen(输出文件 生成器选项...)：输出放在当前构建目录。
# -gen-dialect-decls 生成方言类声明；-dialect=toy 选择方言名称。
mlir_tablegen(ToyDialect.h.inc -gen-dialect-decls -dialect=toy)
# -gen-dialect-defs 生成方言的相关实现；两行使用的是同一份 .td 输入。
mlir_tablegen(ToyDialect.cpp.inc -gen-dialect-defs -dialect=toy)
# 把这组生成任务汇总为具名构建目标，方便其他目标依赖它。
# ToyDialectIncGen 是构建目标名，不是库名或 C++ 类名。
add_public_tablegen_target(ToyDialectIncGen)

# 切换输入文件，接下来的生成任务处理 Operation 定义。
set(LLVM_TARGET_DEFINITIONS include/Toy/ToyOps.td)
# -gen-op-decls / -gen-op-defs 分别生成 Operation 类声明和相关实现。
mlir_tablegen(ToyOps.h.inc -gen-op-decls)
mlir_tablegen(ToyOps.cpp.inc -gen-op-defs)
# 这是另一组生成任务，与上面的 ToyDialectIncGen 分开管理。
add_public_tablegen_target(ToyOpsIncGen)

# add_library(目标名 源文件...)：用这些 .cpp 定义一个库目标。
# 这里省略 STATIC/SHARED，库类型由 BUILD_SHARED_LIBS 控制，默认通常是静态库。
# .cpp 中会包含生成的 .inc，因此 .inc 不必单独列为编译单元。
add_library(ToyDialect lib/ToyDialect.cpp lib/ToyOps.cpp)
# target_include_directories(目标名 作用范围 目录...)：给指定目标设置搜索路径。
# PUBLIC：本库编译时使用，链接本库的其他目标也会获得这些使用要求。
# 相比前面的目录级 include_directories，这里明确描述库对使用者的要求。
target_include_directories(ToyDialect PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR})
# SYSTEM 和 PUBLIC 可以组合：公开传递第三方系统头文件目录。
target_include_directories(ToyDialect SYSTEM PUBLIC ${MLIR_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS})
# add_dependencies(目标 依赖目标...)：确保生成任务先完成，再编译依赖它们的代码。
# 这负责构建先后顺序，不负责链接库。
add_dependencies(ToyDialect ToyDialectIncGen ToyOpsIncGen)
# target_link_libraries(目标 作用范围 库目标...)：声明链接依赖。
# 下列名称是 MLIR 提供的 CMake 目标，携带库位置及相关使用要求。
# PUBLIC 同时向本库的使用者传递这些链接依赖。
target_link_libraries(ToyDialect PUBLIC
  MLIRIR MLIRSideEffectInterfaces MLIRInferTypeOpInterface)

# add_executable(目标名 源文件...)：定义可执行程序，main() 位于该源文件中。
add_executable(toy-opt tools/toy-opt.cpp)
# 工具包含的头文件也会引用 .inc，因此明确依赖生成任务。
add_dependencies(toy-opt ToyDialectIncGen ToyOpsIncGen)
# PRIVATE：这些是当前程序自身的链接依赖，不作为公开接口使用要求发布。
# ToyDialect：自定义方言；MLIROptLib：MlirOptMain；MLIRFuncDialect：函数方言。
target_link_libraries(toy-opt PRIVATE ToyDialect MLIROptLib MLIRFuncDialect)

# 第二个程序：通过 C++ API 创建 IR，而不是读取已有文本。
add_executable(toy-build tools/toy-build.cpp)
add_dependencies(toy-build ToyDialectIncGen ToyOpsIncGen)
# 它没有调用 MlirOptMain，因此这里不需要 MLIROptLib。
target_link_libraries(toy-build PRIVATE ToyDialect MLIRFuncDialect)

# 加载 CTest 模块，提供 BUILD_TESTING 选项；开启时启用测试支持。
include(CTest)
# if(条件) ... endif()：CMake 的条件块，不使用 C++ 的花括号。
# AND：两个条件都满足；STREQUAL：比较字符串是否相同。
# CMAKE_SOURCE_DIR 是整个构建的顶层源码目录。
# 与当前目录相同，表示 Lab2 正独立构建；被 Lab3 作为子目录复用时不登记本组测试。
if(BUILD_TESTING AND CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  # find_program(结果变量 NAMES 候选名... HINTS 提示路径... REQUIRED)：寻找程序。
  # 找到的完整路径保存在 FILECHECK_EXECUTABLE；找不到就报错。
  find_program(FILECHECK_EXECUTABLE NAMES FileCheck-20 FileCheck
    HINTS "${LLVM_TOOLS_BINARY_DIR}" REQUIRED)
  # 只要求 Python 解释器组件，不要求 Python 开发头文件和链接库。
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  # add_test(NAME 测试名 COMMAND 程序 参数...)：登记命令，稍后由 ctest 执行。
  # 此处配置 CMake 时不会立即运行 tests/run.py。
  # 实际命令：Python解释器 run.py toy-opt路径 FileCheck路径 toy-build路径。
  # $<TARGET_FILE:目标名> 是生成器表达式：在生成构建系统时取得目标最终文件路径。
  # 它与 ${变量名} 不同，避免手动拼接可执行文件的目录和平台后缀。
  add_test(NAME toy-dialect-tests
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/run.py
      $<TARGET_FILE:toy-opt> ${FILECHECK_EXECUTABLE} $<TARGET_FILE:toy-build>)
endif()
