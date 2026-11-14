# Lab2：创建自定义 ToyDialect

零基础学习请先看 [图解教程](TUTORIAL.md)，本文保留较详细的实现与运行参考。

本实验已经提供完整实现。学习时先运行，再按下面步骤阅读和修改；不需要先自行补齐代码。

新增动手任务：[toy.mul TODO 清单](TODO.md)。在标注的源码与测试区域独立完成定义、Verifier、注册检查及正反例测试；乘法练习目前保留为空白，不影响已有功能。

目标是让自己的工具识别、验证并打印以下 IR：

```mlir
module {
  func.func @main() -> i32 {
    %a = toy.constant 10 : i32
    %b = toy.constant 20 : i32
    %sum = toy.add %a, %b : i32
    return %sum : i32
  }
}
```

本实验定义独立的标量整数 ToyDialect，支持 i32、i64；它不是 LLVM 官方 Toy 教程的张量方言。加法采用模 2^N 的整数语义，与无溢出标志的 `arith.addi` 一致，为 Lab3 的转换提供基础。本阶段只定义和验证 IR，尚未把加法执行成数值结果。

## 第 1 步：编译并观察输出

```bash
cd ~/projects/mlir-learning/lab02-toy-dialect
cmake -S . -B build -G Ninja \
  -DMLIR_DIR=/usr/lib/llvm-20/lib/cmake/mlir \
  -DLLVM_DIR=/usr/lib/llvm-20/lib/cmake/llvm
cmake --build build -j 2
./build/toy-opt test.mlir --verify-each
ctest --test-dir build --output-on-failure
```

预期输出的 Operation 与输入相同，SSA 名称可能改变。`toy-opt` 是我们编译的工具，负责识别 ToyDialect；系统自带的 `mlir-opt-20` 未链接这个方言，不能直接完成同样的语义验证。使用 `--allow-unregistered-dialect` 也不能代替本实验的注册和验证。

先回答：Lab1 输入中的 `arith.addi` 是谁定义的？这里的 `toy.add` 又是谁定义的？

## 第 2 步：认识文件结构

```text
lab02-toy-dialect/
├── CMakeLists.txt
├── include/Toy/
│   ├── ToyDialect.td      # Dialect 的 TableGen 定义
│   ├── ToyOps.td          # Operation 的 ODS 定义
│   ├── ToyDialect.h       # 引入生成的 Dialect 声明
│   └── ToyOps.h           # 引入生成的 Operation 声明
├── lib/
│   ├── ToyDialect.cpp    # 注册 Operation
│   └── ToyOps.cpp        # 手写 Verifier
├── tools/
│   ├── toy-opt.cpp       # 解析、验证和打印工具
│   └── toy-build.cpp     # 用 C++ API 构造同样的 IR
├── test.mlir
└── tests/
    ├── valid.mlir
    ├── invalid.mlir
    └── run.py
```

构建时在 `build/` 生成四个文件：`ToyDialect.h.inc`、`ToyDialect.cpp.inc`、`ToyOps.h.inc`、`ToyOps.cpp.inc`。它们是 C++ 片段，由手写的头文件或源文件包含。修改 `.td` 后重新构建，不要直接修改 `.inc`。

## 第 3 步：理解 TableGen 如何定义 Dialect

打开 [ToyDialect.td](include/Toy/ToyDialect.td)：

```tablegen
def Toy_Dialect : Dialect {
  let name = "toy";
  let cppNamespace = "::mlir::toy";
}
```

`def` 定义一条 TableGen record，`Dialect` 是它的基类。`name` 决定文本中的方言前缀 `toy`；`cppNamespace` 决定生成类所在的 C++ 命名空间。

`mlir_tablegen(... -gen-dialect-decls)` 生成类声明，`-gen-dialect-defs` 生成定义。TableGen 本身不是 C++ 编译器：它先生成 C++，之后再由 C++ 编译器处理。

先回答：`toy` 和 `mlir::toy` 为什么可以分别设置？

## 第 4 步：理解 Operation 定义

打开 [ToyOps.td](include/Toy/ToyOps.td)。`Toy_Op` 是公共基类，把 Operation 绑定到 ToyDialect。`Toy_AddOp` 的助记名为 `add`，所以 IR 名称为 `toy.add`，生成的类为 `mlir::toy::AddOp`。

```tablegen
let arguments = (ins AnySignlessInteger:$lhs, AnySignlessInteger:$rhs);
let results = (outs AnySignlessInteger:$result);
```

这声明两个输入 SSA Value 和一个输出 SSA Value，生成 `getLhs()`、`getRhs()`、`getResult()` 等访问接口。`AnySignlessInteger` 表示无符号性标记的整数类型，例如 `i32`，不表示只支持非负数，也不等于显式的 unsigned 类型 `ui32`。

`SameOperandsAndResultType` 要求两个输入和结果类型相同。`Pure` 声明这个操作无内存副作用且可推测执行，允许后续优化安全地删除无用计算；它不会自动把加法算成常量。

```tablegen
let assemblyFormat = "$lhs `,` $rhs attr-dict `:` type($result)";
```

这是文本语法的声明。`$lhs`、`$rhs` 是变量，反引号中的逗号和冒号是字面符号，`attr-dict` 保留额外属性的位置。因为三个类型相同，文本只需要打印结果类型，解析器即可推导输入类型。

`toy.constant` 的 `value` 是带类型的编译期属性，结果则是运行在 IR 数据流中的 SSA Value。`AllTypesMatch<["value", "result"]>` 保证属性类型与结果类型相同，解析器可以从 `10 : i32` 推导结果类型。

先回答：`toy.constant` 的数值为什么属于 attribute，而 `toy.add` 的 lhs、rhs 属于 operand？

## 第 5 步：理解 C++ 注册链

按下面顺序阅读：

1. [toy-opt.cpp](tools/toy-opt.cpp)：`registry.insert<ToyDialect, FuncDialect>()` 将方言加入注册表；`MlirOptMain` 提供标准解析、验证、打印和命令行处理。
2. [ToyDialect.cpp](lib/ToyDialect.cpp)：方言初始化时，`addOperations<...>()` 将各个 Operation 注册到方言。
3. [ToyOps.h](include/Toy/ToyOps.h)：`GET_OP_CLASSES` 选择生成文件中的类声明。
4. `build/ToyOps.h.inc`：搜索 `class AddOp`、`getLhs`、`static void build`，观察 ODS 生成的 API。

`GET_OP_LIST` 和 `GET_OP_CLASSES` 是选择生成文件不同部分的预处理宏，不是运行时调用。只在 `.td` 定义 Operation 而不把生成的类注册到方言，工具仍无法正常识别它。

先回答：将 Dialect 加入 registry 和在 Dialect 内注册 Operation，分别解决什么问题？

## 第 6 步：亲手观察 Verifier

本实验有两层验证：ODS 生成的约束负责操作数数量、基础类型以及类型一致性；[ToyOps.cpp](lib/ToyOps.cpp) 中手写的 `verify()` 再要求位宽只能是 32 或 64。`hasVerifier = 1` 让 TableGen 声明这个成员函数，其实现仍由我们编写。

运行所有预期失败案例：

```bash
./build/toy-opt tests/invalid.mlir --split-input-file --verify-diagnostics
```

`--split-input-file` 将 `// -----` 分隔的片段分别处理；`--verify-diagnostics` 检查错误是否与 `expected-error` 注释一致。因此这里返回成功表示“预期的错误全部出现”，不表示输入合法。

观察真正的非零退出码，可以单独建立临时输入：

```bash
printf 'module { func.func @bad() -> i16 { %%c = toy.constant 1 : i16 return %%c : i16 } }\n' \
  | ./build/toy-opt
echo $?
```

输出应包含 `only supports scalar i32 or i64`，退出码为非零。

测试中的错误分工如下：

| 输入问题 | 检查来源 |
| --- | --- |
| 常量结果为 i16 | ConstantOp 的手写 Verifier |
| 加法类型为 i8 | AddOp 的手写 Verifier |
| 加法两个输入类型不一致 | SameOperandsAndResultType |
| 常量属性为 i32，结果为 i64 | AllTypesMatch |
| 浮点加法 | AnySignlessInteger |

类型不一致的案例使用 `"toy.add"(...) : (...) -> ...` 通用语法，显式描述输入输出类型，避免简写语法的解析阶段先报错。通用语法不会绕过 Verifier。

## 第 7 步：用 C++ API 创建 IR

```bash
./build/toy-build
./build/toy-build | ./build/toy-opt --verify-each
./build/toy-opt test.mlir --mlir-print-op-generic
```

打开 [toy-build.cpp](tools/toy-build.cpp)，按以下顺序理解：加载方言 → 创建 ModuleOp → 创建 func.func → 添加入口块 → 设置插入位置 → 创建常量与加法 → 创建 return → verify → 打印。

关键调用：

```cpp
auto a = builder.create<mlir::toy::ConstantOp>(loc, builder.getI32IntegerAttr(10));
auto sum = builder.create<mlir::toy::AddOp>(loc, a.getResult(), b.getResult());
```

这些 builder 由 TableGen 生成，常量结果类型从属性推导，加法结果类型从操作数推导。创建操作时不自动完成全部语义验证，所以程序末尾显式调用 `verify`。`OpBuilder` 用来构造新 IR；Lab1 的 `PatternRewriter` 还会通知重写驱动器 IR 发生了哪些修改。

## 第 8 步：学习验收

先在不修改代码的情况下，解释从 `.td` 到工具识别 `toy.add` 的完整链路，并说明为什么非法 i16 常量能解析但不能通过语义验证。

再独立完成两项练习：

1. 将支持范围扩展到 i16，调整 Verifier、说明和测试。`tests/invalid.mlir` 中原先期望失败的 i16 案例也必须更新。
2. 增加 `toy.mul`：参考 AddOp 定义、实现位宽验证，加入正例和反例，重新构建并运行 CTest。

本实验的完整实现仍保留原始 i32/i64 范围，没有提前替你完成练习。

## 衔接 Lab3

[Lab3 教程](../lab03-dialect-conversion/README.md) 已提供完整转换实现：复用 ToyDialect 库，把 `toy.constant` 转为 `arith.constant`、`toy.add` 转为 `arith.addi`。使用 ConversionTarget 声明合法方言、ConversionPattern 描述替换、TypeConverter 描述类型映射，并用 applyFullConversion 保证非法 Toy Operation 全部消除。本实验复用内置整数类型，因此先采用恒等类型映射；自定义类型转换可在后续练习中增加。
