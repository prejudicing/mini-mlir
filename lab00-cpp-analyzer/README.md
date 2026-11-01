# Lab00：认识 MLIR C++ API

零基础学习请先看 [图解教程](TUTORIAL.md)，本文保留简要运行说明。

保留最初的分析程序，目录由 `mlir-cpp-analyzer` 改为 `lab00-cpp-analyzer`。

在项目根目录运行：

```bash
bash scripts/build-and-test.sh lab00-cpp-analyzer
```

程序读取 `test.mlir`，通过 ModuleOp.walk 找出 arith.addi 并输出操作数、结果和类型信息。阅读顺序：注册方言 → 创建 MLIRContext → parseSourceFile → PassManager → runOnOperation → walk。

学习验收：能够区分 Operation、Value、Type，并解释为什么 `getLhs()` 返回的是 Value，而不是 C++ 整数。随后进入 Lab1，实现真正修改 IR 的优化。
