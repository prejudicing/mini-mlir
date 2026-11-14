"""Generate the Lab3 CTest flow SVG; --png additionally needs CairoSVG.

For Chinese PNG text, configure fontconfig with an available Chinese font.
"""
import argparse
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1440, 1720
parts = []


def text(x, y, value, size=22, color="#334155", anchor="middle", bold=False):
    parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
                 f'font-family="Noto Sans SC, Microsoft YaHei, sans-serif" font-size="{size}" '
                 f'font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')


def box(x, y, width, height, title, lines, color="#2563eb", fill="#ffffff"):
    parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                 f'rx="14" fill="{fill}" stroke="{color}" stroke-width="2"/>')
    text(x + width / 2, y + 35, title, 25, color, bold=True)
    for index, line in enumerate(lines):
        text(x + width / 2, y + 68 + index * 29, line, 20)


def arrow(points):
    path = "M " + " L ".join(f"{x},{y}" for x, y in points)
    parts.append(f'<path d="{path}" fill="none" stroke="#64748b" '
                 'stroke-width="3" marker-end="url(#arrow)"/>')


def generate():
    parts.clear()
    parts.extend([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">Lab3 CTest 调用流程</title>',
        '<desc id="desc">CMake 登记测试后，CTest 启动 lit；lit 加载配置并执行 RUN 指令；'
        '正常转换使用 FileCheck，错误用例使用 verify-diagnostics，最终汇总退出状态。</desc>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 Z" '
        'fill="#64748b"/></marker></defs>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#f5f8fd"/>',
    ])
    text(720, 52, "Lab3：从 CTest 到转换 Pass 的调用流程", 34, "#0f172a", bold=True)
    text(720, 91, "前置条件：工具已构建；CTest 本身不会自动编译 C++", 22)

    box(150, 125, 1140, 120, "准备阶段：CMake 配置", [
        "add_lab_lit_test(toy-convert-opt) → add_test(NAME Lab03-lit ...)",
        "生成 build/tests/lit.site.cfg.py，并登记启动 lit 的命令"], "#64748b", "#f1f5f9")
    arrow([(720, 245), (720, 275)])
    box(150, 275, 1140, 110, "① 用户运行 CTest", [
        "ctest --test-dir lab03-dialect-conversion/build --output-on-failure"])
    arrow([(720, 385), (720, 415)])
    box(150, 415, 1140, 110, "② CTest 执行登记的 Lab03-lit 测试", [
        "python3 /usr/lib/llvm-20/build/utils/lit/lit.py -v <Lab3>/build/tests"])
    arrow([(720, 525), (720, 555)])
    box(150, 555, 1140, 125, "③ lit 加载配置文件", [
        "build/tests/lit.site.cfg.py：设置工具路径 → load_config(...) 加载 tests/lit.cfg.py",
        "lit.cfg.py：指定 .mlir 测试、Shell 执行方式，以及工具占位符替换规则"])
    arrow([(720, 680), (720, 710)])
    box(150, 710, 1140, 120, "④ lit 找到测试文件，读取 // RUN: 指令", [
        "%toy-opt → toy-convert-opt 路径；%FileCheck → FileCheck 路径",
        "%s → 当前测试文件路径（lit 内置），随后交给 Shell 执行"])

    arrow([(720, 830), (720, 850), (365, 850), (365, 880)])
    arrow([(720, 850), (1075, 850), (1075, 880)])
    box(45, 880, 640, 130, "⑤ A．正常转换测试：tests/convert.mlir", [
        "%toy-opt %s --convert-toy-to-arith --verify-each",
        "| %FileCheck %s"], "#059669")
    box(755, 880, 640, 130, "⑤ B．预期失败测试：tests/illegal.mlir", [
        "%toy-opt %s --allow-unregistered-dialect",
        "--convert-toy-to-arith --verify-diagnostics"], "#d97706")
    arrow([(365, 1010), (365, 1040)])
    arrow([(1075, 1010), (1075, 1040)])
    box(45, 1040, 640, 175, "⑥ 转换程序内部", [
        "main()：注册方言、注册转换 Pass",
        "MlirOptMain：解析输入并选择命令行指定的 Pass",
        "runOnOperation() → applyFullConversion()",
        "转换规则创建 Arith Operation，输出 IR"], "#059669")
    box(755, 1040, 640, 175, "⑥ 转换程序内部", [
        "同样启动转换 Pass",
        "unknown.work 无法合法化，产生错误诊断",
        "--verify-diagnostics 对照 expected-error 注释",
        "诊断符合预期 → 测试命令返回成功"], "#d97706")
    arrow([(365, 1215), (365, 1245)])
    box(45, 1245, 640, 125, "⑦ FileCheck 检查输出文本", [
        "读取同一测试文件里的 CHECK / CHECK-LABEL 等规则",
        "确认转换结果出现 arith.*，并满足匹配顺序"], "#059669")
    box(755, 1245, 640, 125, "注意：两种检查方式不同", [
        "正常转换：FileCheck 检查输出 IR",
        "预期错误：工具自身检查诊断；这条 RUN 不调用 FileCheck"], "#d97706", "#fffbeb")
    arrow([(365, 1370), (365, 1400), (720, 1400), (720, 1430)])
    arrow([(1075, 1215), (1415, 1215), (1415, 1400), (720, 1400)])
    box(150, 1430, 1140, 110, "⑧ lit 汇总各测试中 RUN 命令的执行结果", [
        "所有命令满足成功条件 → PASS；出现不符合预期的失败 → FAIL"], "#7c3aed")
    arrow([(720, 1540), (720, 1570)])
    box(150, 1570, 1140, 105, "⑨ CTest 汇总并返回结果", [
        "展示通过 / 失败；--output-on-failure 在失败时展示测试输出"], "#7c3aed")
    text(720, 1703, "说明：convert.mlir 还有一次连续运行转换的检查；图中展示其首条 RUN 和两类测试路径。", 17)
    parts.append("</svg>")
    path = OUT / "ctest-call-flow.svg"
    path.write_text("\n".join(parts) + "\n")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    path = generate()
    if args.png:
        import cairosvg
        cairosvg.svg2png(url=str(path), write_to=str(path.with_suffix(".png")))
    print(path)
