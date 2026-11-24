# Lab1：Pattern Rewrite 与 Greedy Rewrite

文件结构与职责：[PNG 图](diagrams/file-structure.png) · [可缩放 SVG](diagrams/file-structure.svg)。

零基础学习请先看 [图解教程](TUTORIAL.md)，本文保留实现与运行参考。

目标：实现整数加法 `x + 0 → x`，验证驱动器能连续处理多个 Operation，且保留不匹配的加法。

## 编译和运行

在本目录执行（Ubuntu + MLIR 20）：

```bash
cmake -S . -B build -G Ninja \
  -DMLIR_DIR=/usr/lib/llvm-20/lib/cmake/mlir \
  -DLLVM_DIR=/usr/lib/llvm-20/lib/cmake/llvm
cmake --build build -j 2
mlir-opt-20 test.mlir --verify-each
./build/mlir-pattern-rewrite test.mlir
bash tests/run.sh
```

检查脚本使用 `mlir-opt-20`、`FileCheck-20` 和 `diff`。输出中的 SSA 名称由打印器决定，不应通过 `%a`、`%zero` 等名字判断语义。

预期输出：

```mlir
module {
  func.func @main() -> i32 {
    %c10_i32 = arith.constant 10 : i32
    return %c10_i32 : i32
  }
  func.func @test_no_opt() -> i32 {
    %c10_i32 = arith.constant 10 : i32
    %c20_i32 = arith.constant 20 : i32
    %0 = arith.addi %c10_i32, %c20_i32 : i32
    return %0 : i32
  }
}
```

## 理解 main.cpp

数据流：输入文件 → `parseSourceFile` → `ModuleOp` → `PassManager` → `SimplifyAddZeroPass` → Greedy Rewrite 调用 `AddZeroPattern` → 打印 IR。

### Pattern：局部匹配和替换

- `OpRewritePattern<arith::AddIOp>`：限定要匹配的 Operation 类型。
- `using ...::OpRewritePattern`：继承基类构造函数，允许传入 MLIRContext。
- `matchAndRewrite`：由驱动器调用；满足条件时修改 IR 并返回成功，否则返回失败。
- `op.getRhs()`：取得右操作数，是一个 SSA Value。
- `matchPattern(..., m_Zero())`：判断这个 Value 是否是可匹配的零常量，检查值而非名字。
- `rewriter.replaceOp(op, op.getLhs())`：将 addi 结果的所有使用替换为左操作数，并删除 addi；驱动器也会收到修改通知。

例如先消除 `%b = %a + 0`，使用 `%b` 的下一条加法会自动改成使用 `%a`。驱动器也可能先处理后面的加法，因此不要依赖具体处理顺序。

### Pass：组织规则和驱动器

- `OperationPass<ModuleOp>`：Pass 在 module 上运行，驱动器处理其内部的 Operation。
- `RewritePatternSet`：收集规则；`patterns.add<AddZeroPattern>` 注册本实验规则。
- `FrozenRewritePatternSet`：将规则集合冻结，供驱动器使用。
- `config.fold = false`：关闭驱动器的内置常量折叠。否则 `10 + 20` 可能直接变成 `30`，加零也可能由内置折叠完成，难以验证自定义 Pattern。
- `applyPatternsGreedily`：维护工作列表，反复尝试规则直到不再变化或达到限制。
- `signalPassFailure()`：如果驱动器未能收敛，将失败传给 PassManager。

Greedy Rewrite 仍可能删除无用代码，因此优化后 `%zero` 常量也会消失。关闭 folding 并不表示关闭所有清理行为。

### main：解析、执行、输出

注册 Arith 和 Func dialect 后创建上下文，解析文件；将 Pass 加入 PassManager，启用验证并运行；成功后把优化后的 module 打印到标准输出。错误信息写到标准错误，返回非零退出码。

## 两个思考题

1. 单次 `matchAndRewrite` 只处理一个 Operation，Greedy 驱动器负责连续尝试多个 Operation，并在修改后重新考虑受影响的 Operation。不过本例两个 addi 一开始就都能匹配，一次完整遍历也可能处理完；不能用它证明必须进行多轮遍历。
2. `10 + 20` 的右操作数不是零，因此 AddZeroPattern 返回失败，不修改它。保留该加法的前提还包括关闭驱动器的内置 folding。

## 验收和自行修改

`test.mlir` 检查两条加零消除、普通常量加法保留。`tests/edge-cases.mlir` 检查参数参与的三条加零连续消除，以及右侧非零、左侧为零、右侧为未知参数时均保留。脚本还验证输入输出合法、再次优化不再变化，以及错误处理。

建议先自行解释 `replaceOp` 为什么会更新 return 和下一条 addi，然后尝试扩展 `0 + x → x`：增加左操作数为零的匹配，替换为右操作数，并更新 `zero_on_left` 的测试预期。当前实现只要求右侧为零。
