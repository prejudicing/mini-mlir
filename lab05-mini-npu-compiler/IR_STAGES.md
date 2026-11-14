# Lab5：观察每个阶段的 IR

在项目根目录运行：

```bash
python3 lab05-mini-npu-compiler/scripts/dump_ir_stages.py --mode both
```

脚本使用实际的 `npu-opt`、`npu-translate` 逐阶段生成文件，并用模拟器验证最终指令。首次使用前先构建 Lab5。默认输入为 `examples/matmul.mlir`，tile-size=4、SRAM=4096 字节。

打开 [完整阶段对照](build/ir-stages/README.md)，其中按处理顺序嵌入了全部 IR 和最终伪指令，支持直接阅读。该文件属于运行产物，若尚未生成，先执行上述命令。

| 阶段 | FP32 路径文件 | 看什么变化 |
| --- | --- | --- |
| 输入 | [00-linalg.mlir](build/ir-stages/fp32/00-linalg.mlir) | linalg.matmul；A=5×7、B=7×6、C=5×6 |
| 方言转换 | [01-npu.mlir](build/ir-stages/fp32/01-npu.mlir) | 操作变为 npu.matmul；参数类型、形状保持 |
| 分块 | [03-tiled.mlir](build/ir-stages/fp32/03-tiled.mlir) | 生成 8 个 npu.tile，最后一个尺寸为 1×2×3 |
| 内存规划 | [04-planned.mlir](build/ir-stages/fp32/04-planned.mlir) | 参数增加外部地址；tile 增加 SRAM 地址 |
| 指令生成 | [05-program.npu](build/ir-stages/fp32/05-program.npu) | 一个 tile 对应 3 条 LOAD2D、1 条 MATMUL、1 条 STORE2D |

INT8 分支位于 [int8/](build/ir-stages/int8)，在方言转换和分块之间多出 [02-quantized.mlir](build/ir-stages/int8/02-quantized.mlir)。观察 A/B 元素类型从 f32 变成 i8，C 从 f32 变成 i32，函数增加量化属性；之后地址和加载字节数相应变化。

本次 INT8 展示使用示例 scaleA=0.125、scaleB=0.25。它只说明编译表示变化，不代表针对一份实际浮点数据完成了校准。模拟器测试使用其自动生成的数据；要观察真实浮点数据校准、量化与反量化误差，请运行 `python3 lab05-mini-npu-compiler/int8_demo.py`。

## FP32 地址如何对应指令

完整矩阵的外部内存地址：A=0、B=192、C=384。第一个 4×4×4 tile 的 SRAM 地址：A=0、B=64、C=128，峰值需求为 192 字节。

第一个 tile 生成：

```text
LOAD2D g=0 s=0 rows=4 cols=4 stride=7 bytes=4
LOAD2D g=192 s=64 rows=4 cols=4 stride=6 bytes=4
LOAD2D g=384 s=128 rows=4 cols=4 stride=6 bytes=4
MATMUL a=0 b=64 c=128 m=4 n=4 k=4
STORE2D s=128 g=384 rows=4 cols=4 stride=6 bytes=4
```

其中 g/s 是字节地址，stride 是完整矩阵每行的元素数；C 在每个 K 分块前加载旧值、计算后写回，保持累加语义。

## 自己改变分块大小

使用独立目录，保留默认结果：

```bash
python3 lab05-mini-npu-compiler/scripts/dump_ir_stages.py \
  --mode both --tile-size 2 \
  --output-dir lab05-mini-npu-compiler/build/ir-stages-tile2
```

预测：tile 数变成 ceil(5/2)×ceil(6/2)×ceil(7/2)=36；实际数值结果应保持正确。

脚本只执行、导出已有 Pass，不修改 `.td`、C++ 转换规则或模拟器。
