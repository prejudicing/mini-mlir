# Lab3：Dialect Conversion

文件结构与职责：[PNG 图](diagrams/file-structure.png) · [可缩放 SVG](diagrams/file-structure.svg)。

零基础学习请先看 [图解教程](TUTORIAL.md)，本文保留实现与运行参考。

本实验已实现完整转换 Pass，并复用 Lab2 的 ToyDialect 库。目标是把所有 `toy.constant`、`toy.add` 转成 Arith Operation，同时保持数据依赖与 i32/i64 类型。

## 1. 运行完整实验

在项目根目录执行：

```bash
bash scripts/build-and-test.sh lab03-dialect-conversion
cd lab03-dialect-conversion
./build/toy-convert-opt tests/convert.mlir --convert-toy-to-arith --verify-each
```

`@main` 的关键输出：

```mlir
%c10_i32 = arith.constant 10 : i32
%c0_i32 = arith.constant 0 : i32
%0 = arith.addi %c10_i32, %c0_i32 : i32
%1 = arith.addi %0, %c0_i32 : i32
return %1 : i32
```

这里专门只做转换，因此加零操作保留。它们会在 Lab4 的优化 Pipeline 中消除。

## 2. 先认识四个角色

| API | 在本实验中的职责 |
| --- | --- |
| ConversionTarget | 声明 Module、Func、Arith 合法，Toy 非法 |
| TypeConverter | 将源类型映射为目标类型；此处 i32/i64 直接保留 |
| OpConversionPattern | 类型安全的 ConversionPattern，描述一个 Toy Op 如何改写 |
| applyFullConversion | 运行转换，并要求处理范围内全部 Operation 最终合法 |

Lab1 的 Greedy Rewrite 在没有更多规则可用时就可以成功，允许未匹配的操作保留。Full Conversion 还必须满足合法性约束：即使规则已经无法继续匹配，存在非法或未被认可为合法的操作仍然失败。

## 3. 阅读转换规则

打开 [ConvertToyToArith.cpp](lib/ConvertToyToArith.cpp)。先读 `ConvertAdd`：

```cpp
rewriter.replaceOpWithNewOp<arith::AddIOp>(op,
    adaptor.getLhs(), adaptor.getRhs());
```

`replaceOpWithNewOp` 创建目标 Operation，替换原结果的使用并删除旧 Operation。`OpAdaptor` 提供已转换并重映射后的输入值；如果某个输入的定义已经从 Toy 转为 Arith，新加法必须引用转换后的结果。不要依赖转换规则的具体处理顺序。

再读 `ConvertConstant`：保留 value 属性，通过 `getTypeConverter()->convertType` 取得目标结果类型，创建 `arith.constant`。

本实验继承 `OpConversionPattern<T>`，它是 `ConversionPattern` 的类型化封装，能够直接接收具体 Operation 和对应 Adaptor。

## 4. 阅读 TypeConverter

```cpp
TypeConverter types;
types.addConversion([](Type type) { return type; });
```

这里使用恒等映射，因为源方言已经使用目标方言支持的内置整数类型。它不是实际位宽变换，也不需要插入 materialization。后续如果改为 `!toy.int` 等自定义类型，就必须进一步处理函数签名、块参数、调用和返回值，并按需要提供 materialization。

练习前先解释：为什么这次必须学 TypeConverter，却可以不改变类型？

## 5. 阅读合法性声明

```cpp
target.addLegalOp<ModuleOp>();
target.addLegalDialect<func::FuncDialect, arith::ArithDialect>();
target.addIllegalDialect<toy::ToyDialect>();
```

`func.func` 和 `func.return` 在本阶段只负责容纳和传递结果，原样保留。Toy Operation 必须被规则替换。未知操作没有合法性声明，也无法通过这个 Full Conversion。

查看 `tests/illegal.mlir`，运行：

```bash
./build/toy-convert-opt tests/illegal.mlir \
  --allow-unregistered-dialect --convert-toy-to-arith --verify-diagnostics
```

允许解析未注册方言并不等于允许它通过 ConversionTarget。测试要求出现 `failed to legalize operation 'unknown.work'`。

## 6. 理解测试与构建依赖

`CMakeLists.txt` 将 Lab2 作为子目录复用，但不把 Lab2 的独立工具默认加入构建。链接 ToyConversion 会先生成 Toy 的 TableGen 文件并构建 ToyDialect。

`tests/convert.mlir` 检查连续 SSA 依赖、i32/i64、再次转换；`tests/illegal.mlir` 检查完整转换失败。`lit` 从 RUN 注释读取命令，FileCheck 检查输出。可单独运行：

```bash
cmake --build build --target check-toy-convert-opt
```

## 7. 学习验收与修改练习

能解释“重写成功”和“转换后全部合法”的区别；能说明为什么使用 adaptor；能指出 TypeConverter 的作用和当前恒等映射的局限。

自行修改：在 Lab2 的练习中增加 `toy.mul` 后，先观察 Full Conversion 因缺少规则而失败，再添加对应 Arith 转换并补测试。每次修改后重新构建和运行检查。

下一步进入 [Lab4](../lab04-compiler-pipeline/README.md)，把转换和优化串成 Pipeline，并继续降低到 LLVM。
