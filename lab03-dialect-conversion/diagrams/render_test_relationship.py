"""Render CMake / CTest / lit / FileCheck relationships; --png needs CairoSVG."""
import argparse
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent
parts = []


def text(x, y, value, size=22, color="#334155", bold=False, anchor="middle"):
    parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
                 f'font-family="Noto Sans SC, Microsoft YaHei, sans-serif" font-size="{size}" '
                 f'font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')


def box(x, y, w, h, title, lines, color="#2563eb", fill="white"):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" '
                 f'fill="{fill}" stroke="{color}" stroke-width="2"/>')
    text(x+w/2, y+36, title, 26, color, True)
    for i, line in enumerate(lines):
        text(x+w/2, y+72+i*31, line, 21)


def arrow(points, color="#64748b"):
    path = "M " + " L ".join(f"{x},{y}" for x, y in points)
    parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3" '
                 'marker-end="url(#arrow)"/>')


def generate():
    parts.clear()
    parts.extend([
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1750" '
        'viewBox="0 0 1600 1750" role="img" aria-labelledby="title desc">',
        '<title id="title">Lab3：CMake、CTest、lit 和 FileCheck 的关系</title>',
        '<desc id="desc">同一个 MLIR 测试文件中的 RUN、CHECK 与 IR 正文由不同工具读取。'
        'FileCheck 同时接收输出文本与检查规则，捕获 SSA 名称并核对返回值。</desc>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 Z" '
        'fill="#64748b"/></marker></defs>',
        '<rect width="1600" height="1750" fill="#f5f8fd"/>',
    ])
    text(800, 52, "Lab3：谁执行命令，谁读取注释，谁检查输出？", 33, "#0f172a", True)
    text(800, 92, "重点：FileCheck 有两份输入——待检查的程序输出，以及测试文件里的 CHECK 规则。", 22)

    box(60, 130, 680, 130, "CMake：配置与登记", [
        "构建 toy-convert-opt；生成 lit.site.cfg.py",
        "add_test(...) 登记启动 lit 的命令"])
    arrow([(740, 195), (850, 195)])
    text(795, 177, "登记", 19)
    box(850, 130, 680, 130, "CTest：统一测试入口", [
        "用户运行 ctest --test-dir build ...",
        "CTest 执行已登记的测试命令，启动 lit"])
    arrow([(1190, 260), (1190, 320)])
    box(60, 320, 680, 160, "lit 配置：提供路径和规则", [
        "lit.site.cfg.py：具体工具路径，加载 lit.cfg.py",
        "lit.cfg.py：寻找 .mlir、执行 Shell 命令",
        "替换 %toy-opt / %FileCheck；%s 是内置占位符"], "#64748b", "#f1f5f9")
    arrow([(740, 400), (850, 400)])
    text(795, 382, "读取", 19)
    box(850, 320, 680, 160, "lit：找到文件并读取 RUN", [
        "不负责理解 IR 语义，也不负责执行 CHECK 匹配",
        "将 RUN 中的占位符替换为实际路径",
        "通过 Shell 启动转换程序和 FileCheck"])
    arrow([(1190, 480), (1190, 550)])

    box(60, 550, 680, 420, "同一份测试文件：tests/convert.mlir", [], "#7c3aed")
    text(400, 630, "A．RUN 注释：给 lit 的执行命令", 23, "#2563eb", True)
    text(400, 665, "// RUN: %toy-opt %s ... | %FileCheck %s", 20)
    text(400, 730, "B．CHECK 注释：给 FileCheck 的匹配规则", 23, "#d97706", True)
    text(400, 765, "// CHECK: %[[B:.*]] = arith.addi ...", 20)
    text(400, 798, "// CHECK: return %[[C]] : i32", 20)
    text(400, 863, "C．IR 正文：给转换程序的输入", 23, "#059669", True)
    text(400, 900, "module { func.func @main() ... toy.add ... }", 20)
    text(400, 941, "对 MLIR 解析器，RUN / CHECK 都是普通注释。", 19)
    arrow([(740, 630), (850, 630)])
    text(795, 612, "RUN", 19)
    box(850, 550, 680, 210, "占位符展开后，命令效果相当于", [
        "./build/toy-convert-opt tests/convert.mlir",
        "--convert-toy-to-arith --verify-each",
        "| FileCheck-20 tests/convert.mlir",
        "左边程序的标准输出，经管道交给右边程序"])
    box(880, 815, 620, 155, "下面两条箭头分别表示输入数据来源", [
        "IR 正文 → toy-convert-opt",
        "CHECK 规则 → FileCheck",
        "RUN 命令负责将两个程序组织成管道"], "#64748b", "#f1f5f9")

    arrow([(400, 970), (400, 1060)])
    text(400, 1010, "读取 IR 正文，解析成内存 IR", 20, "#059669")
    arrow([(740, 780), (795, 780), (795, 1150), (850, 1150)])
    text(770, 1020, "CHECK 规则", 19, "#d97706", anchor="end")
    box(60, 1060, 640, 195, "toy-convert-opt：执行转换 Pass", [
        "Toy IR → Arith IR → 打印标准输出",
        "例如输出：",
        "%0 = arith.addi %arg0, %arg1 : i32",
        "return %0 : i32"], "#059669")
    arrow([(700, 1210), (755, 1210), (755, 1300), (1190, 1300), (1190, 1255)])
    text(1040, 1330, "待检查文本：标准输出，经 Shell 管道传递", 20, "#059669")
    box(850, 1060, 680, 195, "FileCheck：将规则与输出进行匹配", [
        "一份输入：从 stdin 接收转换后的 IR 文本",
        "另一份输入：从测试文件读取 CHECK 规则",
        "按顺序匹配；捕获并复用 SSA 名称",
        "匹配成功返回 0；不符合要求则返回失败"], "#d97706")

    box(60, 1390, 1470, 210, "单独理解你问的 SUM 捕获语法（示意，不是当前测试文件的原样内容）", [
        "// CHECK: %[[SUM:.*]] = arith.addi    → 在示例输出中捕获 SUM = 0",
        "// CHECK: return %[[SUM]] : i32      → 要求后面出现 return %0 : i32",
        "因此既检查存在加法，也检查返回的是那条加法的结果；打印器换成 %7 也能匹配。",
        "只有引用 [[SUM]] 而没有前面的捕获定义不够；SUM 不是 C++ 变量。"], "#7c3aed")
    text(800, 1650, "结果返回：FileCheck 的退出状态 → lit 判定该 RUN / 测试是否通过 → CTest 汇总。", 23, "#0f172a", True)
    text(800, 1700, "CMake / CTest 不解释 CHECK；lit 负责执行 RUN；FileCheck 负责解释 CHECK。", 22)
    parts.append('</svg>')
    path = OUT / 'test-tools-relationship.svg'
    path.write_text('\n'.join(parts) + '\n')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--png', action='store_true')
    args = parser.parse_args()
    path = generate()
    if args.png:
        import cairosvg
        cairosvg.svg2png(url=str(path), write_to=str(path.with_suffix('.png')))
    print(path)
