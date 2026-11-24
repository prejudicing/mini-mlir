"""Render annotated source trees for every lab; --png additionally needs CairoSVG.

Markdown/HTML documents and generated build directories are omitted. Existing
illustration directories are represented as collapsed nodes, not recursively drawn.
"""
import argparse
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMON = {
    'CMakeLists.txt': '配置构建目标、链接依赖及测试入口',
    'tests/lit.cfg.py': '设置 lit 的测试发现、Shell 格式及命令替换规则',
    'tests/lit.site.cfg.py.in': '由 CMake 填入工具路径，生成 build 中的 lit 配置',
}
LABS = {
'lab00-cmake-demo': ('Lab00 · 第一个 C++ 工程', {
    'CMakeLists.txt': '定义 C++17 可执行目标 my_program，生成构建规则',
    'main.cpp': '程序入口：输出文本，练习配置、编译和运行',
}),
'lab00-calculator-tests': ('Lab00 · 计算器与测试工程', {
    'main.cpp': '整数计算器：加减乘除、参数检查及错误退出码',
    'tests/arithmetic.test': '四则运算：RUN 执行命令，FileCheck 检查输出',
    'tests/boundaries.test': '检查负数、零、大整数和整数除法边界',
    'tests/check_error.py': '检查退出码为 2 且 stdout 为空，转发诊断文本',
    'tests/errors.test': '检查除零、未知操作及非法输入的错误信息',
    'tests/usage.test': '检查参数数量错误时的用法提示',
}),
'lab00-cpp-analyzer': ('Lab00 · MLIR C++ 分析器', {
    'CMakeLists.txt': '查找 MLIR，设置 C++17、头文件路径与分析器链接库',
    'main.cpp': '解析 MLIR，运行分析 Pass，遍历并统计 arith.addi',
    'test.mlir': '分析器输入：包含整数常量、加法与函数',
}),
'lab01-pattern-rewrite': ('Lab01 · Pattern Rewrite', {
    'main.cpp': '定义加零规则与 Pass，使用 Greedy 驱动重写并打印 IR',
    'test.mlir': '主示例：连续加零消除，非匹配加法保留',
    'tests/edge-cases.mlir': '覆盖多种匹配及不应重写的边界情况',
    'tests/run.sh': '运行 Verifier、FileCheck、重复运行一致性及失败用例',
}),
'lab02-toy-dialect': ('Lab02 · 自定义 Toy 方言', {
    'include/Toy/ToyDialect.h': '方言公开声明：包含 TableGen 生成的方言头文件',
    'include/Toy/ToyDialect.td': 'TableGen 方言定义：名称、C++ 命名空间等',
    'include/Toy/ToyOps.h': '操作公开声明：包含生成的 Op 类及所需接口',
    'include/Toy/ToyOps.td': '定义 constant/add/mul 的约束、文本格式和 Verifier 声明',
    'lib/ToyDialect.cpp': '实现 initialize，将生成的操作类型注册进方言',
    'lib/ToyOps.cpp': '包含生成的操作实现，手写常量和整数位宽验证',
    'tools/toy-build.cpp': '通过 C++ OpBuilder 创建并验证 Toy IR，然后打印',
    'tools/toy-opt.cpp': '注册方言，调用 MlirOptMain 提供解析、验证、打印入口',
    'test.mlir': '基础 Toy IR 示例及输出检查规则',
    'tests/valid.mlir': '合法输入：覆盖常量、加法、乘法及不同整数位宽',
    'tests/invalid.mlir': '非法输入：配合 expected-error 检查诊断',
    'tests/run.py': '组织 FileCheck、解析打印往返、Verifier 与 builder 测试',
}),
'lab03-dialect-conversion': ('Lab03 · Toy → Arith', {
    'include/ToyConversion.h': '声明转换 Pass 创建函数与注册函数',
    'lib/ConvertToyToArith.cpp': '定义 ConversionPattern、类型映射与 Full Conversion',
    'tools/toy-convert-opt.cpp': '注册 Toy/Arith/Func 方言及转换 Pass，启动 opt 驱动',
    'tests/convert.mlir': '检查 Toy 常量、加法转换为 Arith 后的数据依赖',
    'tests/illegal.mlir': '检查非法操作无法完成 Full Conversion 的失败诊断',
}),
'lab04-compiler-pipeline': ('Lab04 · 编译流水线与 LLVM', {
    'include/Pipelines.h': '公开声明实验 Pass/Pipeline 注册入口',
    'lib/Pipelines.cpp': '操作统计、加零优化及优化/LLVM Lowering 两条流水线',
    'tools/compiler-opt.cpp': '注册方言与流水线，通过 MlirOptMain 处理命令行',
    'tests/arguments.mlir': '检查带函数参数时加零消除与普通加法保留',
    'tests/check_exit.py': '执行程序并检查退出码，验证 lli 返回值',
    'tests/pipeline.mlir': '检查优化 IR、分析统计、LLVM IR 导出和 lli 执行',
}),
'lab05-mini-npu-compiler': ('Lab05 · Mini NPU 编译器', {
    'include/NPU/Compiler.h': '声明 Pass 注册与伪指令发射接口',
    'include/NPU/NPU.h': '公开方言/操作声明、验证函数及字节数/对齐工具',
    'include/NPU/NPU.td': '定义 npu.matmul、npu.tile 的参数、格式与验证入口',
    'lib/NPUDialect.cpp': '注册 NPU 操作，验证矩阵、量化元数据和 tile 边界',
    'lib/Passes.cpp': 'Linalg Lowering、INT8 接口转换、分块及 DRAM/SRAM 规划',
    'lib/Emitter.cpp': '将规划后的 tile 发射为 LOAD2D、MATMUL、STORE2D 等文本',
    'tools/npu-opt.cpp': '编译驱动入口：解析 IR，运行单个 Pass 或 npu-compile',
    'tools/npu-translate.cpp': '发射工具入口：读取规划后的 IR，输出伪指令程序',
    'simulator.py': '功能模型：解释伪指令，模拟内存搬运与 FP32/INT8 计算',
    'quantize.py': '宿主侧 AbsMax 校准、实际数据量化、反量化和重定标',
    'int8_demo.py': '组织真实浮点数据的 INT8 编译、模拟执行和误差验证',
    'examples/matmul.mlir': 'FP32 输入示例：5×7 与 7×6 的 buffer 矩阵乘加',
    'examples/matmul-int8.mlir': '原生整数输入示例：i8×i8→i32 累加',
    'examples/quantization-input.json': 'INT8 演示使用的真实浮点输入数据及矩阵尺寸',
    'scripts/dump_ir_stages.py': '逐阶段调用编译工具，保存各层 IR、伪指令与模拟报告',
    'tests/capacity.mlir': '检查 tile 所需 SRAM 超过容量时拒绝编译',
    'tests/int8-invalid.mlir': '检查非法 INT8 矩阵类型组合的诊断',
    'tests/int8.mlir': '检查量化后的类型、scale、内存规划和整数指令',
    'tests/int8_numerical.py': 'INT8 精确计算、量化误差和非法参数的回归验证',
    'tests/invalid.mlir': '检查形状、布局、操作等不合法情况的诊断',
    'tests/numerical.py': '多种形状/分块/种子下验证 FP32 数值与累加语义',
    'tests/pipeline.mlir': '检查 Lowering、内存属性及最终伪指令文本',
}),
'lab06-pytorch-to-npu': ('Lab06 · PyTorch → Mini NPU', {
    'model.py': '最小 PyTorch 模型：两个输入，只计算 A @ B',
    'frontend.py': '导出/检查 ATen 图，分析静态形状，生成 Linalg buffer IR',
    'run.py': '编排编译与数据流：调用 Lab5、模拟执行、对照 PyTorch',
    'requirements.txt': '声明独立环境中的 CPU PyTorch、NumPy 依赖版本',
    'scripts/setup.sh': '建立 build/venv，安装实验需要的 Python 依赖',
    'scripts/render-diagrams.py': '生成本实验已有的前端、ABI 和流水线图解',
    'examples/inputs.json': '可手算的 A/B 矩阵输入，用于端到端演示',
    'tests/run.py': '端到端与反例测试：数值、导出、ABI、阶段一致性等',
}),
}
DIRS = {
    'include': '公开 C++ / TableGen 定义', 'include/Toy': 'Toy 方言与操作接口',
    'include/NPU': 'NPU 方言与编译接口', 'lib': '方言、Pass 或代码生成实现',
    'tools': '命令行可执行工具入口', 'tests': '自动化测试与测试配置',
    'examples': '示例 IR 与输入数据', 'scripts': '安装、导出或图解辅助脚本',
    'diagram': '已有流程图与生成脚本（保留，不展开）',
    'diagrams': '流程图与本文件结构图（不展开图片）',
    'docs': '已有图解资源（不展开）',
}
SKIP = {'build', '.git', '__pycache__', '.venv'}
COLLAPSE = {'diagram', 'diagrams', 'docs'}


def entries(lab, descriptions):
    """Read the real filesystem; fail on an undocumented source file."""
    def visit(folder, prefix=''):
        children = []
        for path in folder.iterdir():
            if path.name in SKIP or path.name.startswith('.'):
                continue
            if path.is_file() and path.suffix.lower() in ('.md', '.html'):
                continue
            children.append(path)
        children.sort(key=lambda p: (not p.is_dir(), p.name))
        rows = []
        for index, path in enumerate(children):
            last = index == len(children) - 1
            rel = path.relative_to(lab).as_posix()
            branch = '└── ' if last else '├── '
            if path.is_dir():
                label = path.name + '/'
                description = DIRS.get(rel, DIRS.get(path.name, '源码分组'))
                rows.append((prefix + branch + label, description, True))
                if path.name not in COLLAPSE:
                    rows.extend(visit(path, prefix + ('    ' if last else '│   ')))
            else:
                if rel not in descriptions and rel not in COMMON:
                    raise ValueError(f'Add a description for {lab.name}/{rel}')
                rows.append((prefix + branch + path.name,
                             descriptions.get(rel, COMMON.get(rel)), False))
        return rows
    return [(lab.name + '/', '实验源码根目录', True)] + visit(lab)


def render(lab, title, descriptions, png):
    out = lab / 'diagrams'
    out.mkdir(exist_ok=True)
    rows = entries(lab, descriptions)
    width, row_height, start_y = 1900, 42, 208
    height = start_y + len(rows) * row_height + 76
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}：文件结构与职责</title>',
        '<desc id="desc">文件树左侧展示源码路径，右侧说明用途；不介绍 Markdown/HTML 文档，不展开 build 生成目录和图片资源。</desc>',
        f'<rect width="{width}" height="{height}" fill="#f5f8fd"/>',
        '<style>text {font-family:"Noto Sans SC","Microsoft YaHei",sans-serif;} .tree {font-family:"DejaVu Sans Mono","Noto Sans SC",monospace;white-space:pre;}</style>',
        f'<text x="48" y="58" font-size="32" font-weight="700" fill="#0f172a">{escape(title)} · 文件结构与职责</text>',
        '<text x="48" y="100" font-size="20" fill="#475569">只介绍程序、配置、测试与输入数据；省略 Markdown/HTML 文档、build 生成产物及图片明细。</text>',
        '<text x="48" y="155" font-size="22" font-weight="700" fill="#334155">文件结构</text>',
        '<text x="770" y="155" font-size="22" font-weight="700" fill="#334155">用途 / 在实验中的职责</text>',
    ]
    for i, (label, detail, directory) in enumerate(rows):
        y = start_y + i * row_height
        if i % 2 == 0:
            parts.append(f'<rect x="32" y="{y-29}" width="1836" height="42" rx="5" fill="#eaf0f8"/>')
        parts.append(f'<text class="tree" xml:space="preserve" x="48" y="{y}" font-size="21" fill="{"#1d4ed8" if directory else "#0f172a"}" font-weight="{700 if directory else 400}">{escape(label)}</text>')
        parts.append(f'<text x="770" y="{y}" font-size="21" fill="#334155">{escape(detail)}</text>')
    parts.append(f'<text x="48" y="{height-28}" font-size="18" fill="#64748b">按实际源码目录生成 · 重新生成：python3 scripts/render-lab-file-trees.py --png（PNG 需要 CairoSVG 与中文字体）</text>')
    parts.append('</svg>')
    svg = out / 'file-structure.svg'
    svg.write_text('\n'.join(parts) + '\n')
    if png:
        import cairosvg
        cairosvg.svg2png(url=str(svg), write_to=str(out / 'file-structure.png'))
    print(f'{lab.name}: {len(rows)} rows -> {svg.relative_to(ROOT)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--png', action='store_true')
    args = parser.parse_args()
    for name, (title, descriptions) in LABS.items():
        render(ROOT / name, title, descriptions, args.png)


if __name__ == '__main__':
    main()
