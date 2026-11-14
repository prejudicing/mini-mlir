"""Generate Lab4 call-flow SVGs; --png additionally needs CairoSVG and Chinese fonts."""
import argparse
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent


class Diagram:
    def __init__(self, title, subtitle, height):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="{height}" '
            f'viewBox="0 0 1440 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 Z" '
            'fill="#64748b"/></marker></defs>',
            f'<rect width="1440" height="{height}" fill="#f5f8fd"/>',
        ]
        self.text(720, 52, title, 33, "#0f172a", True)
        self.text(720, 92, subtitle)

    def text(self, x, y, value, size=21, color="#334155", bold=False):
        self.parts.append(f'<text x="{x}" y="{y}" text-anchor="middle" '
                          f'font-family="Noto Sans SC, Microsoft YaHei, sans-serif" font-size="{size}" '
                          f'font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')

    def box(self, x, y, w, h, title, lines, color="#2563eb", fill="white"):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                          f'rx="14" fill="{fill}" stroke="{color}" stroke-width="2"/>')
        self.text(x + w / 2, y + 34, title, 25, color, True)
        for i, line in enumerate(lines):
            self.text(x + w / 2, y + 66 + 29 * i, line, 20)

    def arrow(self, points):
        path = "M " + " L ".join(f"{x},{y}" for x, y in points)
        self.parts.append(f'<path d="{path}" fill="none" stroke="#64748b" '
                          'stroke-width="3" marker-end="url(#arrow)"/>')

    def save(self, name):
        path = OUT / f'{name}.svg'
        path.write_text('\n'.join(self.parts + ['</svg>']) + '\n')
        return path


def pipeline():
    d = Diagram("Lab4：程序入口、流水线注册与执行", "选择一条命令行流水线；注册、构建流水线、执行 IR 是三个不同阶段。", 2030)
    d.box(100, 125, 1240, 120, "① 程序启动：tools/compiler-opt.cpp → main()", [
        "创建 DialectRegistry，登记 Toy / Arith / Func / LLVM 方言",
        "调用 registerLab4Pipelines()，然后进入 MlirOptMain(argc, argv, ..., registry)"])
    d.arrow([(720, 245), (720, 275)])
    d.box(100, 275, 1240, 145, "② 注册阶段：lib/Pipelines.cpp → registerLab4Pipelines()", [
        "注册单个 Pass：Toy → Arith、AnalyzePass、SimplifyPass",
        "注册流水线名称：lab4-optimize、lab4-lower-to-llvm，以及各自的 Lambda 构建回调",
        "此时只登记创建方式；尚未运行 Pattern，也没有修改输入 IR"], "#64748b", "#f1f5f9")
    d.arrow([(720, 420), (720, 450)])
    d.box(100, 450, 1240, 120, "③ MlirOptMain 根据命令行组织任务", [
        "处理参数、加载所需方言、解析并验证输入 IR",
        "查找所选流水线，调用注册的 Lambda，把 Pass 按顺序加入管理器"])
    d.arrow([(720, 570), (720, 590), (365, 590), (365, 620)])
    d.arrow([(720, 590), (1075, 590), (1075, 620)])
    d.box(45, 620, 640, 140, "选项 A：--lab4-optimize", [
        "Lambda 调用 buildOptimizePipeline(pm)", "构建 6 个公共优化步骤"], "#059669")
    d.box(755, 620, 640, 140, "选项 B：--lab4-lower-to-llvm", [
        "Lambda 先调用 buildOptimizePipeline(pm)", "再追加 Arith / Func → LLVM 等 3 个步骤"], "#7c3aed")
    d.arrow([(365, 760), (365, 790), (720, 790), (720, 820)])
    d.arrow([(1075, 760), (1075, 790), (720, 790)])
    d.box(100, 820, 1240, 390, "④ 执行阶段：Pass Manager 按流水线顺序调用各 Pass", [
        "1．AnalyzePass：getAnalysis<OperationCounts>() → 打印优化前统计", "↓",
        "2．Toy → Arith：runOnOperation() → applyFullConversion() → 常量 / 加法转换规则", "↓",
        "3．函数级 SimplifyPass：Greedy Rewrite → AddZero → replaceOp()", "↓",
        "4．Canonicalizer：规范化、folding；5．CSE：消除满足安全条件的重复计算", "↓",
        "6．AnalyzePass：获取当前有效的分析结果 → 打印优化后统计"], "#059669")
    d.text(720, 1180, "第 3 步由 addNestedPass<func::FuncOp>() 安排到各函数；其他公共步骤位于外层 Module 流水线。", 20)
    d.arrow([(720, 1210), (720, 1270), (365, 1270), (365, 1300)])
    d.arrow([(720, 1270), (1075, 1270), (1075, 1300)])
    d.box(45, 1300, 640, 140, "A．公共优化完成，输出 Arith MLIR", [
        "MlirOptMain 打印 IR；分析日志写入 stderr", "示例结果：arith.constant 30"], "#059669")
    d.box(755, 1300, 640, 190, "B．继续执行追加的 LLVM 转换", [
        "7．createArithToLLVMConversionPass()", "8．createConvertFuncToLLVMPass()",
        "9．createReconcileUnrealizedCastsPass()", "最后由 MlirOptMain 输出 LLVM Dialect MLIR"], "#7c3aed")
    d.arrow([(1075, 1490), (1075, 1520)])
    d.box(755, 1520, 640, 130, "⑤ 外部命令：导出真正的 LLVM IR", [
        "mlir-translate-20 --mlir-to-llvmir", "lowered.mlir → program.ll"], "#d97706")
    d.arrow([(1075, 1650), (1075, 1680)])
    d.box(755, 1680, 640, 130, "⑥ 外部命令：执行 LLVM IR", [
        "lli-20 program.ll", "运行 @main；示例返回值为 30"], "#d97706")
    d.box(45, 1520, 640, 290, "阅读时要分清", [
        "注册：保存 Pass / 流水线的创建方式", "构建：Lambda 把 Pass 加入 pm",
        "执行：Pass Manager 调用 runOnOperation()", "LLVM Dialect 仍属于 MLIR",
        "导出 LLVM IR 与 lli 执行是后续独立命令", "本例两条流水线的第 1～6 步完全复用"], "#64748b", "#f1f5f9")
    d.box(100, 1850, 1240, 120, "测试入口：CTest → lit → RUN 命令", [
        "RUN 调用 compiler-opt，再用 FileCheck 检查 IR / 日志",
        "完整执行测试还会调用 mlir-translate 和 check_exit.py，核对 lli 返回 30"], "#64748b", "#f1f5f9")
    d.text(720, 2005, "配置依据：tools/compiler-opt.cpp、lib/Pipelines.cpp、tests/pipeline.mlir。箭头表示调用或处理顺序。", 17)
    return d.save('pipeline-call-flow')


def details():
    d = Diagram("Lab4：分析 Pass 与改写 Pass 的内部调用", "两类 Pass 都由 Pass Manager 调用，但分析只读取 IR，改写会改变 IR。", 1090)
    d.box(45, 130, 640, 110, "分析路径：AnalyzePass", ["Module 级 runOnOperation()"])
    d.box(755, 130, 640, 110, "改写路径：SimplifyPass", ["嵌套在 func.func 层级的 runOnOperation()"], "#059669")
    d.arrow([(365, 240), (365, 275)])
    d.arrow([(1075, 240), (1075, 275)])
    d.box(45, 275, 640, 140, "getAnalysis<OperationCounts>()", [
        "分析管理器返回有效缓存", "若没有有效结果，则构造 OperationCounts(root)"])
    d.box(755, 275, 640, 140, "准备规则集合与 Greedy 配置", [
        "patterns.add<AddZero>()；冻结规则集合", "config.fold = false（仅关闭此驱动器的 folding）"], "#059669")
    d.arrow([(365, 415), (365, 450)])
    d.arrow([(1075, 415), (1075, 450)])
    d.box(45, 450, 640, 140, "需要计算时：root->walk(...) 统计", [
        "遍历当前 Module，统计 total / toyAdds / arithAdds", "AnalyzePass 通过 const 引用读取结果"])
    d.box(755, 450, 640, 140, "applyPatternsGreedily(...) 驱动", [
        "处理当前函数内的候选 Operation", "调用 AddZero::matchAndRewrite(op, rewriter)"], "#059669")
    d.arrow([(365, 590), (365, 625)])
    d.arrow([(1075, 590), (1075, 625)])
    d.box(45, 625, 640, 165, "打印统计，并声明保留分析", [
        "llvm::errs() 输出报告，不修改 IR", "markAllAnalysesPreserved()",
        "后续修改 IR 的 Pass 仍可能使旧结果失效"])
    d.box(755, 625, 640, 165, "匹配与改写：x + 0 → x", [
        "RHS 不匹配常量零：failure()，不改写", "匹配零：replaceOp(op, op.getLhs())",
        "更新结果使用关系、删除加法，然后 success()"], "#059669")
    d.arrow([(1075, 790), (1075, 825)])
    d.box(755, 825, 640, 140, "驱动器继续处理受影响的操作", [
        "达到稳定状态；或未能完成时向 Pass 报告失败", "驱动失败 → signalPassFailure() 通知 Pass Manager"], "#059669")
    d.box(45, 825, 640, 140, "注意两种 failure 的层次", [
        "Pattern 不匹配 ≠ 整个 Pass 失败", "打印到 errs() 也不表示 Pass 失败"], "#64748b", "#f1f5f9")
    d.text(720, 1020, "SimplifyPass 关闭 folding，不影响后续独立 Canonicalizer Pass 继续执行 folding。", 21)
    d.text(720, 1060, "分析缓存记录的是某个时刻的 IR 信息，不能在改变 IR 后无条件复用。", 19)
    return d.save('pass-detail-flow')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--png', action='store_true')
    args = parser.parse_args()
    paths = [pipeline(), details()]
    if args.png:
        import cairosvg
        for path in paths:
            cairosvg.svg2png(url=str(path), write_to=str(path.with_suffix('.png')))
    for path in paths:
        print(path)
