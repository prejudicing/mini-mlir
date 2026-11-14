# Lab2 动手练习：自己定义并注册 toy.mul

在指定的 `TODO(LAB2-MUL-数字)` 区域填写代码。当前只有注释和留白，尚未实现乘法；原有 Lab2 仍可构建和测试。这里的验收目标是定义、注册、解析、验证和打印，不包含执行乘法或 Lowering。

暂时保持原有 i32/i64 支持范围，不要同时做教程中扩展 i16 的练习，否则需要调整反例。

## 按这个顺序完成

| 顺序 | 文件与标记 | 你要完成的内容 |
| --- | --- | --- |
| 1 | [ToyOps.td](include/Toy/ToyOps.td)，`LAB2-MUL-1` | 参考 AddOp，定义 Toy_MulOp：名称、性质、输入、结果、文本格式、自定义验证声明 |
| 2 | [ToyOps.cpp](lib/ToyOps.cpp)，`LAB2-MUL-2` | 实现 MulOp::verify()，复用位宽检查 |
| 3 | [ToyDialect.cpp](lib/ToyDialect.cpp)，`LAB2-MUL-3` | 阅读注册代码；重新构建后确认生成的 Operation 列表包含 MulOp |
| 4 | [valid.mlir](tests/valid.mlir)，`LAB2-MUL-4` | 新增 i32/i64 两个合法乘法函数，并在文件顶部添加 FileCheck 检查 |
| 5 | [invalid.mlir](tests/invalid.mlir)，`LAB2-MUL-5` | 新增 i16、混合位宽、浮点类型的非法乘法用例与预期诊断 |

第 1、2 步建议一起完成后再构建。只声明自定义 Verifier 而不实现，可能导致链接失败；实现时类尚未生成，也可能导致编译失败。

注册步骤是理解现有自动注册机制，不要求为了练习而改坏它。工具已注册 ToyDialect；新操作通常不需要修改 toy-opt.cpp、头文件或 CMake。所有生成的 `.inc` 文件由构建系统更新。

## 构建与验收

在项目根目录运行：

```bash
bash scripts/build-and-test.sh lab02-toy-dialect
```

然后进入 Lab2：

```bash
cd lab02-toy-dialect

# 查看生成的类和类型列表；要在实际的 GET_OP_LIST 分支中检查注册列表。
rg -n 'class MulOp|GET_OP_LIST|mlir::toy::MulOp' build/ToyOps.h.inc build/ToyOps.cpp.inc

# 合法输入必须通过，并在输出中保留 toy.mul。
./build/toy-opt tests/valid.mlir --verify-each

# 所有预期错误必须出现；命令成功不代表其中的 IR 合法。
./build/toy-opt tests/invalid.mlir --split-input-file --verify-diagnostics

# 自动检查输出、往返解析、诊断和原有 C++ 构造功能。
ctest --test-dir build --output-on-failure
```

空的 TODO 不会让原有测试失败，因此“原有测试通过”不代表乘法练习已经完成。还需要检查你确实新增了两个合法函数和三个非法片段，而且 FileCheck 会检查 toy.mul；仅粘贴 TODO 注释不算完成。

## 提交给自己的一次口头验收

- [ ] 我能解释 .td 中每个字段的用途，而不是只把 add 换成 mul。
- [ ] 我知道 MulOp 的声明和 build/print 等配套实现来自哪里。
- [ ] 我能从 GET_OP_LIST 一路解释到 addOperations 和方言注册。
- [ ] 合法 i32/i64 输入通过，三个反例由正确的验证层拒绝。
- [ ] 我能说明“工具认识乘法”和“工具能执行乘法”的区别。

完成后可以把修改交给助手审查；下一阶段再为它增加 Toy → Arith 的转换规则。
