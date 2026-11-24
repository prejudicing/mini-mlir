# Lab5：Mini NPU Compiler

文件结构与职责：[PNG 图](diagrams/file-structure.png) · [可缩放 SVG](diagrams/file-structure.svg)。

零基础学习请先看 [图解教程：从矩阵到 NPU，再到 INT8](TUTORIAL.md)，本文保留实现与运行参考。

这是可以完整运行的教学编译器：输入 Linalg buffer matmul，输出自定义 NPU 伪指令，并用指令模拟器核对数值。代码、样例、错误案例与自动测试均已实现。

观察完整过程：[逐阶段 IR 与最终伪指令](IR_STAGES.md)。运行 `python3 lab05-mini-npu-compiler/scripts/dump_ir_stages.py --mode both`（在项目根目录）可以导出 FP32/INT8 两条路径的全部表示及可直接阅读的对照文档。

已加入 INT8 量化路径：支持对称逐张量校准、INT8 输入、INT32 累加、混合位宽内存规划和反量化误差验证。先阅读下面的 FP32 基础流程，再进入 [INT8 量化教程](INT8_QUANTIZATION.md)。快速体验：`python3 int8_demo.py`。

下一课：[Lab6：接入 PyTorch 的 A @ B 模型](../lab06-pytorch-to-npu/TUTORIAL.md)。Lab6 复用本实验的后端和模拟器，增加真实模型导出、静态单算子前端、输出 buffer 调用约定和 PyTorch 数值对照。为逐阶段保存 IR，本实验的单独 Pass 也支持 `--npu-tile='tile-size=2'`、`--npu-plan-memory='sram-bytes=512'`。

## 1. 先运行完整流程

在项目根目录执行：

```bash
bash scripts/build-and-test.sh lab05-mini-npu-compiler
cd lab05-mini-npu-compiler
./build/npu-opt examples/matmul.mlir --npu-compile --verify-each \
  -o build/planned.mlir
./build/npu-translate build/planned.mlir > build/program.npu
python3 simulator.py build/program.npu
```

最后应输出 `PASS: 5x7 @ 7x6, initial C preserved, max error=0.0`。

```text
linalg.matmul (C += A*B)
  → convert-linalg-to-npu
npu.matmul
  → npu-tile
npu.tile（M/N/K 分块，处理边界）
  → npu-plan-memory
带 DRAM/SRAM 地址的 npu.tile
  → npu-translate
LOAD2D / MATMUL / STORE2D
  → simulator.py
与标量 f32 参考计算对比
```

## 2. 明确支持的语义

- 每个 kernel 是一个单块、按 A/B/C 顺序传入三个 buffer 参数、无返回值的 `func.func`，每次 matmul 也使用这个顺序。
- A[M,K]、B[K,N]、C[M,N] 为静态、二维、连续行优先、内存空间 0 的 memref，单维在 1 到 4096 之间。元素类型可为 f32/f32/f32，或有符号解释的 i8/i8/i32。
- kernel 可包含一个或多个顺序执行的标准 buffer `linalg.matmul`，语义为 **C += A × B**，C 的初值可以非零。
- 调用约定要求三个实参 buffer 互不重叠；编译器会拒绝输入和输出为相同 SSA Value 的明显别名，但无法仅靠类型判断外部指针是否重叠。
- tile 大小可配置，范围为 1 到 64，默认 4；每个 matmul 最多展开为 100000 个 tile。
- SRAM 默认 4096 字节，DRAM 和 SRAM 分配按 64 字节对齐。

本项目提供软件 NPU 模型和伪 ISA，不连接真实硬件。动态 shape、tensor bufferization、自定义转置/广播 maps、自动搜索 tile、异步 DMA、双缓冲、通用图内存分配和硬件二进制编码不在当前实现范围内。

## 3. 文件阅读顺序

```text
include/NPU/NPU.td    Dialect 和两种 Operation
lib/NPUDialect.cpp   注册与 Verifier
lib/Passes.cpp       Lowering、Tiling、Memory Planning 和 Pipeline
lib/Emitter.cpp      检查规划并生成伪指令
tools/npu-opt.cpp    标准 MLIR 优化工具入口
tools/npu-translate.cpp 伪指令导出入口
simulator.py         指令解释与数值核对
quantize.py          主机侧数据校准、量化、反量化和可选重定标
int8_demo.py         带真实 FP32 数据的 INT8 编译与误差演示
tests/               lit/FileCheck、Verifier、容量与数值测试
```

## 4. 定义 NPU Dialect

打开 [NPU.td](include/NPU/NPU.td)：`npu.matmul` 是整矩阵操作，`npu.tile` 是局部 M/N/K 分块。这些操作通过修改 C 的内存产生结果，没有 SSA result。

两种操作都没有声明 `Pure`。如果将有写内存效果的操作错误标记为 Pure，后续优化可能把没有 SSA 使用的计算删除。本实验使用保守的副作用模型；更完整的实现可以声明精确的 MemoryEffectOpInterface 读写效果。

| tile 属性 | 含义 |
| --- | --- |
| m、n、k | 当前分块在全矩阵的起始坐标 |
| tm、tn、tk | 当前分块实际覆盖的 M/N/K 长度 |

Verifier 检查 memref 类型、布局、矩阵尺寸关系、明显别名与 tile 范围。先用 `tests/invalid.mlir` 看错误，再阅读 [NPUDialect.cpp](lib/NPUDialect.cpp) 的检查顺序。

## 5. Linalg → NPU Lowering

```bash
./build/npu-opt examples/matmul.mlir --convert-linalg-to-npu --verify-each
```

`LowerMatmul` 使用 OpConversionPattern，把 buffer `linalg.matmul` 替换为 `npu.matmul`。ConversionTarget 将 Linalg 声明为非法，只有可处理的操作才能通过完整转换。

规则检查标准 indexing maps：A 使用 (m,k)，B 使用 (k,n)，C 使用 (m,n)。自定义转置或广播不能直接套用此规则，否则地址计算会错误。

这里不新建输出 buffer：Linalg 的 outs 参数直接成为 NPU 的 C，保持原来的累加语义。

## 6. 手写 Tiling

```bash
./build/npu-opt examples/matmul.mlir \
  --convert-linalg-to-npu --npu-tile --verify-each
```

本实验在 C++ 中显式展开三个循环：

```cpp
for (m = 0; m < M; m += tileSize)
  for (n = 0; n < N; n += tileSize)
    for (k = 0; k < K; k += tileSize)
      createTile(m, n, k,
                 min(tileSize, M - m),
                 min(tileSize, N - n),
                 min(tileSize, K - k));
```

5×7 与 7×6 的矩阵乘法在 tile-size=4 时产生 2×2×2=8 个 tile。最后一个 tile 从 (4,4,4) 开始，实际大小为 (1,2,3)，不能仍然按 4×4×4 读写。

这是针对该操作的手写静态分块，没有调用 Linalg 通用 tiling 接口。

先回答：为什么 K 也要分块？同一个 C tile 在两个 K 分块之间如何保持累加结果？

## 7. Memory Planning

```bash
./build/npu-opt examples/matmul.mlir --npu-compile -o build/planned.mlir
```

函数参数带 `npu.address`、`npu.bytes` 属性。示例 A 为 140 字节、B 为 168 字节、C 为 120 字节，按 64 字节对齐后，地址依次为 0、192、384。

每个 tile 的三个 SRAM 区域：A 从 0 开始，占 tm*tk*4 字节；B 从 A 的对齐结束地址开始，占 tk*tn*4 字节；C 从 B 的对齐结束地址开始，占 tm*tn*4 字节。4×4×4 tile 的三个区域各占 64 字节，共 192 字节。

每个 tile 的 DMA、计算、写回同步完成，之后 scratch buffer 可被下一 tile 重用。这个规划器实现 tile 生命周期复用，没有实现任意计算图的存活区间分配。

改变配置：

```bash
./build/npu-opt examples/matmul.mlir \
  --npu-compile="tile-size=2 sram-bytes=256" --verify-each
```

如果设置 `sram-bytes=128`，默认 tile 需要 192 字节，编译应报告容量错误。即使 tile 很小，三个区域的 64 字节对齐也会带来空间开销。

## 8. 生成伪指令

打开 [Emitter.cpp](lib/Emitter.cpp)。它先验证 module，重新核对 DRAM/SRAM 地址和容量，随后才输出完整程序。缺少规划或篡改出重叠地址时，导出失败，不输出半份指令。

示例第一个 tile：

```text
FUNC matmul sram=192
BUFFER id=0 g=0 rows=5 cols=7
BUFFER id=1 g=192 rows=7 cols=6
BUFFER id=2 g=384 rows=5 cols=6
LOAD2D g=0 s=0 rows=4 cols=4 stride=7
LOAD2D g=192 s=64 rows=4 cols=4 stride=6
LOAD2D g=384 s=128 rows=4 cols=4 stride=6
MATMUL a=0 b=64 c=128 m=4 n=4 k=4
STORE2D s=128 g=384 rows=4 cols=4 stride=6
```

`g`、`s` 单位为字节；`rows`、`cols`、`stride` 单位为元素。当前导出器还打印 BUFFER 的 dtype 和 DMA 的 bytes 字段：FP32 元素为 4 字节，INT8 路径的 A/B 元素为 1 字节，C 为 4 字节。DRAM 中每行保持原矩阵 stride，SRAM tile 紧凑排列。

MATMUL 使用独立 f32 乘法和累加的参考语义，不假定融合 FMA。每个 K 分块先加载当前 C，累加本分块，再写回，下一个 K 分块就能读到部分和。该实现会重复搬运 C，后续可以将 C tile 留在 SRAM 减少 DMA。

## 9. 模拟执行与测试

```bash
ctest --test-dir build --output-on-failure
python3 tests/numerical.py ./build/npu-opt ./build/npu-translate
```

lit/FileCheck 检查 Lowering、分块坐标、对齐地址和伪指令；诊断检查覆盖非法 shape、动态维度、tile 越界、别名与 SRAM 不足。

数值测试包含 5 种形状、4 种 tile 大小、3 组随机种子，共 60 组单次 matmul；再检查连续两次 matmul，共 61 组。输入包含负数、分数和非零初始 C。模拟器按字节地址执行 DMA 和计算，检查越界及输入 buffer 未被修改，再与独立标量参考结果比较。另检查非法 Pipeline 参数、未规划输入和被篡改的重叠地址。

模拟器命令行默认核对每个 kernel 的一次矩阵乘加。多次累加测试通过 Python 的 `simulate(..., repeats=2)` 指明参考计算次数。

新增的 `NPU-int8` 检查组运行 63 组整数精确检查、真实数据校准与误差检查，以及量化参数、metadata 和混合位宽内存检查。详见 [INT8 教程](INT8_QUANTIZATION.md)。

## 10. 学习验收与扩展

能从输入 shape 手算 tile 数量、最后一个 tile 大小、每个 buffer 字节数和地址；能解释为什么必须保留 C 的初值，以及 SRAM 何时可以重用。

修改练习：支持非方形 tm/tn/tk 配置；将 C 保留在 SRAM 跨 K 分块累加；增加统计 Pass 报告 tile 数和 DMA 字节数。每次修改后用数值模拟验证语义。
