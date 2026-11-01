# 教程配图

35 张项目自绘图，PNG 用于 Markdown 内联显示，SVG 用于放大和后续修改。每个文件名在两种格式下相同，各 Lab 的 TUTORIAL.md 负责解释对应图示。

内容包括：终端与构建、IR 层次与 SSA、重写和替换、TableGen 和注册、Verifier、类型映射和合法化、Pipeline 和测试、矩阵分块、DRAM/SRAM、DMA、INT8 位宽、舍入与精度检查。

源文件生成器：[render-learning-diagrams.py](../../scripts/render-learning-diagrams.py)。脚本默认只生成 SVG，使用 Python 标准库；`--png` 另外需要 CairoSVG、系统 Cairo 和中文字体。PNG 已随项目提供，阅读教程不需要额外安装。

查看课程入口：[图解学习路线](../../LEARNING_GUIDE.md)。
