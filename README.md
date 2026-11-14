# MLIR 学习实验

环境：Ubuntu 24.04 WSL2，LLVM/MLIR 20。所有实验均提供可运行实现与中文教程，按“先运行成品，再逐步阅读、解释和修改”的方式学习。

**零基础请从 [图解学习路线](LEARNING_GUIDE.md) 开始。** 每个实验提供独立的 TUTORIAL.md，配有概念图、可复制命令、预期结果、常见错误、修改练习与自测答案；原 README 保留为运行和实现参考。Lab00～Lab05 提供 35 张中文图解，Lab06 新增 5 张流程图，均含 PNG 和 SVG。

| 编号 | 目录 | 学习内容与教程 |
| --- | --- | --- |
| Lab00 | `lab00-cmake-demo` | [图解：终端、CMake 与第一个程序](lab00-cmake-demo/TUTORIAL.md) |
| Lab00 | `lab00-cpp-analyzer` | [图解：MLIR C++ API、IR 遍历和分析](lab00-cpp-analyzer/TUTORIAL.md) |
| Lab01 | `lab01-pattern-rewrite` | [图解：加零优化、Pass、Pattern、Greedy Rewrite](lab01-pattern-rewrite/TUTORIAL.md) |
| Lab02 | `lab02-toy-dialect` | [图解：TableGen、ToyDialect、注册与 Verifier](lab02-toy-dialect/TUTORIAL.md) |
| Lab03 | `lab03-dialect-conversion` | [图解：ConversionTarget、Pattern、类型与完整转换](lab03-dialect-conversion/TUTORIAL.md) |
| Lab04 | `lab04-compiler-pipeline` | [图解：Pipeline、IR 分析、LLVM 与测试](lab04-compiler-pipeline/TUTORIAL.md) |
| Lab05 | `lab05-mini-npu-compiler` | [图解：NPU 编译、分块、内存与 INT8](lab05-mini-npu-compiler/TUTORIAL.md)、[量化详细参考](lab05-mini-npu-compiler/INT8_QUANTIZATION.md) |
| Lab06 | `lab06-pytorch-to-npu` | [图解：PyTorch 导出、单算子前端、NPU 编译与数值对照](lab06-pytorch-to-npu/TUTORIAL.md) |

## 一次构建并验证全部实验

```bash
cd ~/projects/mlir-learning
# 首次准备 Lab6 的独立 CPU PyTorch 环境，需要联网下载：
bash lab06-pytorch-to-npu/scripts/setup.sh
bash scripts/build-and-test.sh
```

默认使用 `/usr/lib/llvm-20` 和 2 个编译任务。可配置：

```bash
LLVM_PREFIX=/usr/lib/llvm-20 JOBS=2 bash scripts/build-and-test.sh
bash scripts/build-and-test.sh lab03-dialect-conversion lab04-compiler-pipeline
```

工具需求：CMake、Ninja、C++17 编译器、LLVM/MLIR 20 开发文件和工具、Python3。测试使用 `FileCheck-20`、`mlir-opt-20`、`mlir-translate-20`、`lli-20`，lit 从本机 LLVM 的 `build/utils/lit/lit.py` 调用，无需额外 pip 安装。

各实验可独立配置、构建和测试。Lab3 在构建时复用 Lab2 的方言源码，Lab4 复用 Lab3 的转换库，Lab6 构建并复用 Lab5 后端，无需事先构建前一实验。各自的生成代码和二进制放在 `build/` 中。Lab6 另需独立的 CPU PyTorch 环境，安装和运行方式见其 README。

## 学习与验收

硬件背景资料：[NVIDIA GPU 各代架构硬件资源报告](docs/reports/nvidia-gpu-architecture-resources.md)，包含架构、每 SM 资源、代表 GPU 配置、显存/缓存/互连及官方来源；也提供 [HTML 阅读版](docs/reports/nvidia-gpu-architecture-resources.html) 和 CSV 附件。

建议依次阅读各目录 README。每个阶段先运行得到预期结果，再解释相关源码及输入输出变化，最后完成修改练习。提供完整成品不等于已经完成个人学习验收。

Lab1 检查连续加零重写与非匹配操作保留；Lab2 检查解析、C++ 构建及合法性；Lab3 检查完整转换和失败诊断；Lab4 导出 LLVM IR 并执行，返回 30；Lab5 通过伪指令模拟器检查 61 组数值案例。

Mini NPU Compiler 支持静态二维连续 buffer 矩阵乘加 `C += A*B`，可选择 FP32 或 INT8 输入、INT32 累加，并提供真实数据校准、反量化和误差演示。硬件接口、动态 shape、通用图分配等扩展边界在 Lab5 教程中列明。

Lab6 在此基础上接入只计算 `A @ B` 的 PyTorch 模型：用真实 `torch.export` 捕获图，通过手写的单算子前端生成 Linalg buffer IR，再复用 Lab5 编译和模拟执行，与 PyTorch 对照。支持 FP32 和 INT8；没有调用 Torch-MLIR，也没有实现通用模型前端。

原有准备目录已改名为 `lab00-cmake-demo`、`lab00-cpp-analyzer`；原 Lab1、Lab2 目录已改名为 `lab01-pattern-rewrite`、`lab02-toy-dialect`。移动后的旧 CMake 缓存已清理。根目录原有的 `test.mlir`、`cse.mlir`、`invalid.mlir` 样例继续保留。
