# Mini NPU Compiler：INT8 量化教程

第一次学习矩阵、内存和量化时，请先读 [零基础图解课程](TUTORIAL.md)；本文用于继续深入量化实现与接口。

本扩展提供完整的对称、逐张量 INT8 量化流程：真实浮点数据校准 → 主机侧量化 → 编译整数 kernel → 执行伪指令 → 核对整数参考 → 反量化并测量 FP32 误差。已有 FP32 路径继续可用。

## 1. 先运行带真实数据的演示

在项目根目录执行：

```bash
bash scripts/build-and-test.sh lab05-mini-npu-compiler
cd lab05-mini-npu-compiler
python3 int8_demo.py
```

演示使用固定随机种子生成 5×7 的 A、7×6 的 B 和非零初始 C。校准后的 scale 会传给编译器，同一份 scale 也用于实际输入数据量化。

默认输出约为：

```text
a_scale: 0.015543346329936831
b_scale: 0.015418058305274783
c_scale: 0.00023964821997404489
max_abs_error: 0.04763
rmse: 0.01959
input_bytes_fp32: 308
input_bytes_int8: 77
integer_reference_exact: true
```

`build/int8-demo/` 包含：

| 文件 | 内容 |
| --- | --- |
| input.mlir | 原始 FP32 Linalg kernel |
| planned.mlir | INT8/INT32 类型、scale 和内存规划 |
| program.npu | 可执行的整数伪指令 |
| tensors.json | 原始张量、量化张量、INT32 输出、反量化输出、FP32 参考和误差 |

这里 A、B 的数据容量缩小为四分之一；C 仍为 4 字节累加器，所以不能把“输入缩小 4 倍”理解为整个 kernel 的内存全部缩小 4 倍。

## 2. 理解量化公式

采用零点为 0 的对称量化。校准时对 A、B 各自计算一个 scale：

```text
sA = max(abs(A)) / 127
sB = max(abs(B)) / 127
qA = clamp(round_even(A / sA), -127, 127)
qB = clamp(round_even(B / sB), -127, 127)
```

全零张量使用 scale=1，避免除零。所有 scale 必须有限且严格为正，sA*sB 也不能溢出或下溢为零。舍入采用最接近整数、恰好一半时取偶数；超出范围时饱和。本量化器使用对称窄范围 [-127,127]，原生有符号 i8 kernel 也接受 -128。

本项目的矩阵操作语义一直是 `C += A*B`。因此 C 的初值也需要量化，且使用乘积 scale：

```text
sC = sA * sB
qC_initial = round_even(C_initial / sC)  // INT32
qC_out = qC_initial + sum(sign_extend(qA) * sign_extend(qB))
C_out_approx = qC_out * sC
```

初始 C 不能直接转成 INT8，也不能直接按 sA 或 sB 缩放。不能表示为 INT32 的初值会在主机侧被拒绝。

整数 ISA 的累加按模 2^32 回绕，并解释为有符号 INT32，与 signless i32 加法一致。一般量化推理应避免累加溢出：演示在执行前使用无限精度整数检查输出范围，若溢出则报错；原生整数模拟器还专门测试回绕语义。

先回答：为什么 A、B 可以存 INT8，而 C 必须用 INT32？为什么 C 的 scale 是两个输入 scale 的乘积？

## 3. 看清编译器与主机侧的分工

```text
主机：FP32 A/B/C → 校准 scale → INT8 A/B + INT32 C
                                      ↓
编译：FP32 Linalg → npu.matmul → npu-quantize-int8
                             → npu.tile → Memory Planning → ISA
                                      ↓
执行：主机量化后的数据 → MATMUL_I8 → INT32 输出
                                      ↓
主机：按 sA*sB 反量化，或再量化为 INT8
```

MLIR kernel 的输入是 buffer 参数，编译器看不到 buffer 内的数据。`npu-quantize-int8` 改变函数 ABI、记录 scale 并生成整数运算，实际数据校准和量化由 [quantize.py](quantize.py) 执行。调用者必须传入量化后的数据；不能把原来的 float 指针直接当作 i8 指针使用。

这里实现的是静态逐张量量化，没有使用 MLIR Quant Dialect 或 `!quant.uniform` 类型。scale 作为经过检查的 `npu.*` 函数属性保存；零点固定为 0。每个 kernel 的 A、B 各有一个 scale，同一 kernel 的多次累加共享这些 scale。

## 4. 手动运行量化编译

```bash
./build/npu-opt examples/matmul.mlir \
  --npu-compile="quantize-int8=true a-scale=0.125 b-scale=0.25" \
  --verify-each -o build/int8.mlir
./build/npu-translate build/int8.mlir > build/int8.npu
python3 simulator.py build/int8.npu
```

最后一条使用随机整数输入，检查整数 ISA 是否正确，不测量真实 FP32 输入的量化误差。真实误差请运行 `int8_demo.py`。

也可以单独观察新 Pass：

```bash
./build/npu-opt examples/matmul.mlir \
  --convert-linalg-to-npu \
  --npu-quantize-int8="a-scale=0.125 b-scale=0.25" --verify-each
```

此 Pass 必须在 NPU Lowering 之后、Tiling 之前运行。它将 A、B 的 `memref<...xf32>` 改为 `memref<...xi8>`，C 改为 `memref<...xi32>`，同步更新函数签名，并记录：

```mlir
npu.a_scale = 1.250000e-01 : f64
npu.b_scale = 2.500000e-01 : f64
npu.c_scale = 3.125000e-02 : f64
npu.quantization = "symmetric-per-tensor"
```

Pass 在修改类型前检查整个模块，拒绝重复量化、已分块操作和不支持的类型。输入已经是 INT8 时直接编译，不要再次启用量化：

```bash
./build/npu-opt examples/matmul-int8.mlir --npu-compile --verify-each
```

原生整数输入允许不带 scale，此时仅表示整数矩阵乘加；只有知道输入 scale 后才能解释其浮点含义。前端拒绝 unsigned 扩展，避免把有符号 INT8 误当成 UINT8。

## 5. 观察内存和 ISA 的变化

5×7、7×6、5×6 示例的未对齐容量：

| Buffer | FP32 路径 | INT8 路径 |
| --- | --- | --- |
| A | 140 字节 | 35 字节 |
| B | 168 字节 | 42 字节 |
| C | 120 字节 | 120 字节 |

64 字节对齐后，INT8 路径的三个 DRAM 地址为 0、64、128。SRAM 地址计算、DMA 全局偏移及容量检查都按元素实际字节数计算，而非只改变类型名称。

```text
BUFFER id=0 g=0 rows=5 cols=7 dtype=i8
BUFFER id=1 g=64 rows=7 cols=6 dtype=i8
BUFFER id=2 g=128 rows=5 cols=6 dtype=i32
LOAD2D g=0 s=0 rows=4 cols=4 stride=7 bytes=1
LOAD2D g=64 s=64 rows=4 cols=4 stride=6 bytes=1
LOAD2D g=128 s=128 rows=4 cols=4 stride=6 bytes=4
MATMUL_I8 a=0 b=64 c=128 m=4 n=4 k=4
STORE2D s=128 g=128 rows=4 cols=4 stride=6 bytes=4
```

地址单位为字节，stride 单位仍为元素，`bytes` 声明每个元素的字节数。模拟器检查 DMA 与 buffer 类型的位宽一致性。

4×4×4 tile 因三个区域都按 64 字节对齐，FP32 和 INT8 的 SRAM 占用都为 192 字节。8×8×8 tile 则由 FP32 的 768 字节降到 INT8 的 384 字节：同样的 512 字节 SRAM，FP32 编译失败，INT8 编译成功。这一行为有自动测试。

每个 K 分块仍先加载 INT32 C、累加并写回，直到所有 K 分块完成才在主机反量化；不能在每个 K 分块后将 C 舍入回 INT8，否则会损失部分和精度。

## 6. 使用自己的数据

建立 JSON 文件，包含 m、n、k 和扁平行优先数组 a、b，可选初始 c：

```json
{
  "m": 1, "n": 2, "k": 3,
  "a": [0.5, -1.0, 1.5],
  "b": [0.25, -0.5, 1.0, 0.75, -1.25, 0.5],
  "c": [0.1, -0.2]
}
```

```bash
python3 int8_demo.py --input examples/quantization-input.json \
  --output-dir build/my-int8
```

演示会生成对应 shape 的 MLIR、校准 scale、实际量化数据并执行核对。缺少 c 时默认全零；FP32 ABI 的输入值先按 f32 精度解释。

也可以调用 Python API：

```python
from quantize import calibrate, quantize_int8, dequantize_accumulator, requantize_int8

scale = calibrate([0.5, -1.0, 1.5])
q = quantize_int8([0.5, -1.0, 1.5], scale)
```

需要最终 INT8 输出时，调用 `requantize_int8(qC, sA, sB, output_scale)`。这一步目前在主机侧执行，不是 NPU 的整数重定标指令；NPU 输出保持 INT32。逐通道 scale、非零零点、UINT8、量化感知训练及硬件定点 multiplier/shift 重定标属于后续扩展。

## 7. 代码阅读与验收

建议按以下顺序阅读：

1. [quantize.py](quantize.py)：校准、舍入、饱和、C 初值量化、反量化。
2. [Passes.cpp](lib/Passes.cpp) 的 QuantizePass：函数 ABI 改写和 scale 属性。
3. [NPUDialect.cpp](lib/NPUDialect.cpp)：合法的类型组合和 scale 检查。
4. [Passes.cpp](lib/Passes.cpp) 的 PlanPass 与 [Emitter.cpp](lib/Emitter.cpp)：实际元素位宽和 MATMUL_I8。
5. [simulator.py](simulator.py)：混合位宽 DMA、signed INT8 乘法和 INT32 回绕。
6. [int8_demo.py](int8_demo.py)：实际数据贯穿整个流程，以及 FP32 误差检查。

```bash
ctest --test-dir build --output-on-failure
python3 tests/int8_numerical.py ./build/npu-opt ./build/npu-translate
```

新增 63 组整数精确检查，覆盖不同 tile/shape、K 分块、非零初始 C、重复累加、-128/127 和 INT32 溢出；额外测试舍入、饱和、全零校准、非法 scale、重复量化、metadata 篡改和 SRAM 节省。三组真实 FP32 数据演示检查整数结果完全一致，并检查反量化误差在舍入误差界内。原有 61 组 FP32 回归检查仍运行。

学习验收：能手算一个元素的 qA、qB、qC 和反量化结果，解释为什么“整数结果完全一致”与“相对 FP32 有量化误差”可以同时成立，并说明 scale 和 buffer 的类型、数据必须如何配套。
