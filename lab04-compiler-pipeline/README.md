# Lab4：编译器综合实践

零基础学习请先看 [图解教程](TUTORIAL.md)，本文保留实现与运行参考。

本实验将 Lab1 的重写规则与 Lab3 的转换组合起来，增加缓存式 IR 分析、标准优化、LLVM Lowering 和 lit/FileCheck 测试，最终通过 lli 执行生成的 LLVM IR。

新增 [调用流程图](diagram/README.md)：从 main 和注册回调到两条流水线执行，另附 AnalyzePass 与 SimplifyPass 的内部调用图。

## 1. 构建与运行

在项目根目录执行：

```bash
bash scripts/build-and-test.sh lab04-compiler-pipeline
cd lab04-compiler-pipeline
./build/compiler-opt tests/pipeline.mlir --lab4-optimize --verify-each
```

输入 `(10 + 20) + 0 + 0` 最终成为 `arith.constant 30`。本阶段启用了 canonicalizer，所以 `10 + 20` 会折叠；这与 Lab1 为观察独立 Pattern 而保留该加法的验收目的不同。

## 2. 阅读 Pipeline

打开 [Pipelines.cpp](lib/Pipelines.cpp)，找到 `buildOptimizePipeline`：

```text
lab4-analyze
  → convert-toy-to-arith
  → func.func(lab4-simplify-add-zero)
  → canonicalize
  → cse
  → lab4-analyze
```

`addPass` 添加 module 上运行的 Pass；`addNestedPass<func::FuncOp>` 将函数级 Pass 安排到每个函数。`PassPipelineRegistration` 为完整流水线取名，命令行可以用 `--lab4-optimize` 调用。

先解释：为什么必须先把 `toy.add` 转为 `arith.addi`，Lab1 的加零规则才能匹配？为什么函数级 Pass 不能直接当作 module Pass 使用？

## 3. 观察分析结果和分析缓存

```bash
./build/compiler-opt tests/pipeline.mlir --lab4-optimize -o build/optimized.mlir
```

IR 输出到文件，分析报告写到 stderr。优化前为 `toy.add=3`，优化后为 `toy.add=0 arith.addi=0`。

`OperationCounts(Operation *root)` 遍历当前 module 并统计操作。`getAnalysis<OperationCounts>()` 通过 MLIR 分析管理器按需创建或获取缓存。分析 Pass 不修改 IR，因此调用 `markAllAnalysesPreserved()`；转换和重写修改了 IR，相关缓存会失效，后面的分析得到更新后的结果。

用下面命令看每个 Pass 后的 IR：

```bash
./build/compiler-opt tests/pipeline.mlir --lab4-optimize \
  --mlir-print-ir-after-all -o build/optimized.mlir
```

观察顺序：Toy Operation 消失 → 加零消失 → 普通常量加法折叠。CSE 用于合并公共子表达式；这个简单输入可能在 canonicalizer 后已不再需要进一步修改。

## 4. Lowering 到 LLVM 并执行

`lab4-lower-to-llvm` 在上述优化后继续执行 Arith → LLVM、Func → LLVM，最后清理无用的 unrealized conversion casts。

```bash
./build/compiler-opt tests/pipeline.mlir --lab4-lower-to-llvm \
  --verify-each -o build/lowered.mlir
mlir-translate-20 --mlir-to-llvmir build/lowered.mlir > build/program.ll
lli-20 build/program.ll
echo $?
```

最终退出码应为 `30`，来自 `main` 的返回值。这里非零退出码是被编译程序的预期行为，自动测试专门检查它等于 30。不要把这一步直接放在 `set -e` 脚本中而不处理该退出状态。

MLIR 的 LLVM Dialect 仍然是 MLIR；`mlir-translate` 才将其导出为 LLVM IR，之后由 lli 执行。

## 5. 理解 lit 和 FileCheck

```bash
ctest --test-dir build --output-on-failure
cmake --build build --target check-compiler-opt
```

`lit.cfg.py` 定义测试格式和工具替换，CMake 生成的 `lit.site.cfg.py` 提供绝对工具路径。RUN 行定义具体命令，FileCheck 的 CHECK/CHECK-NOT 检查结果和不应残留的操作，命名捕获检查 SSA 数据流关系。

`tests/pipeline.mlir` 检查优化、分析、LLVM Dialect、LLVM IR 导出和真实执行；`tests/arguments.mlir` 检查未知函数参数参与的加零，以及普通参数加法保留。`check_exit.py` 专门核对 lli 的退出值。

## 6. 学习验收

能解释 Pipeline 中每一步的输入输出、函数级 Pass 的嵌套、分析缓存何时失效，以及 LLVM Dialect 与 LLVM IR 的区别。

修改练习：把输入改为 `40 + 2 + 0`，同步更新常量、FileCheck 和执行返回值；再删除 canonicalizer，观察只做加零优化时的 IR。下一阶段进入 [Mini NPU Compiler](../lab05-mini-npu-compiler/README.md)。
