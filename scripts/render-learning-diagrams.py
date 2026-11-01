#!/usr/bin/env python3
"""Generate tutorial SVGs using stdlib; --png additionally needs cairosvg.

Chinese font fallback: Noto Sans SC, Microsoft YaHei, sans-serif.
For consistent PNGs, configure FONTCONFIG_FILE to point to a Chinese font.
"""
import argparse
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/images"
BLUE, GREEN, ORANGE, PURPLE = "#2563eb", "#059669", "#d97706", "#7c3aed"
INK, GRAY = "#172b4d", "#526580"
COLORS = [BLUE, GREEN, PURPLE, ORANGE, BLUE, GREEN]


class Figure:
    def __init__(self, title, subtitle, height=440):
        self.height = height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="{height}" viewBox="0 0 1440 {height}" role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>',
                      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#526580"/></marker></defs>',
                      '<rect width="1440" height="100%" rx="20" fill="#f5f8fd"/>']
        self.text(42, 53, title, 31, INK, weight="700")
        self.text(42, 91, subtitle, 20, GRAY)

    def text(self, x, y, value, size=23, color=INK, anchor="start", weight="400"):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="Noto Sans SC, Microsoft YaHei, sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{escape(str(value))}</text>')

    def rect(self, x, y, w, h, color="#fff", stroke="#d7e1f1", radius=15):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{color}" stroke="{stroke}" stroke-width="2"/>')

    def arrow(self, x1, y1, x2, y2, label=""):
        self.parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{GRAY}" stroke-width="3" marker-end="url(#arrow)"/>')
        if label:
            self.text((x1+x2)/2, (y1+y2)/2-12, label, 18, GRAY, "middle")

    def card(self, x, y, w, title, lines, color=BLUE, h=150):
        self.rect(x, y, w, h)
        self.rect(x, y, w, 9, color, color, 4)
        self.text(x+w/2, y+47, title, 25, color, "middle", "700")
        for index, line in enumerate(lines):
            self.text(x+w/2, y+86+index*31, line, 21, INK, "middle")

    def save(self, name):
        self.text(42, self.height-22, "MLIR 学习实验 · 图解教程", 16, GRAY)
        self.parts.append('</svg>')
        path = OUT / f"{name}.svg"
        path.write_text("\n".join(self.parts)+"\n")
        return path


def flow(name, title, subtitle, cards, note):
    f = Figure(title, subtitle, 400)
    count = len(cards)
    width = (1330 - (count-1)*46)/count
    for i, (label, *lines) in enumerate(cards):
        x = 55+i*(width+46)
        f.card(x, 145, width, label, lines, COLORS[i % len(COLORS)])
        if i:
            f.arrow(x-39, 220, x-8, 220)
    f.text(720, 343, note, 23, GRAY, "middle")
    return f.save(name)


def compare(name, title, subtitle, left_title, left, right_title, right, note):
    height = 320 + max(len(left), len(right))*40
    f = Figure(title, subtitle, height)
    for x, label, lines, color in [(45, left_title, left, BLUE), (790, right_title, right, GREEN)]:
        f.rect(x, 130, 600, height-205)
        f.text(x+28, 172, label, 26, color, weight="700")
        for i, line in enumerate(lines):
            f.text(x+28, 219+i*39, line, 23)
    f.arrow(670, height/2, 765, height/2)
    f.text(720, height-55, note, 21, GRAY, "middle")
    return f.save(name)


def grid(name, title, subtitle, items):
    rows = (len(items)+1)//2
    f = Figure(title, subtitle, 160+rows*170)
    for i, (heading, line1, line2) in enumerate(items):
        f.card(45+(i%2)*690, 125+(i//2)*170, 660, heading, [line1, line2], COLORS[i%len(COLORS)], 150)
    return f.save(name)


def nesting():
    f = Figure("IR 是一棵有层次的树", "module 包含函数；函数体有块；块中排列 Operation。", 540)
    for x, y, w, h, label, color in [
        (50, 125, 1335, 350, "ModuleOp  ·  module", BLUE),
        (90, 190, 1255, 265, "FuncOp  ·  func.func @main", GREEN),
        (130, 250, 1175, 185, "Block  ·  函数入口块", PURPLE)]:
        f.rect(x,y,w,h,"#fff",color)
        f.text(x+22,y+38,label,25,color,weight="700")
    for i, label in enumerate(["constant 10", "constant 20", "addi", "return"]):
        f.card(160+i*278,315,255,label,["一个 Operation"],COLORS[i],100)
    return f.save("lab00-ir-tree")


def ssa():
    f = Figure("SSA：名字连接的是计算结果", "%a、%b、%c 是 Value；箭头代表某个结果被后续 Operation 使用。", 540)
    f.card(55,140,285,"constant 10",["结果：%a : i32"],BLUE)
    f.card(55,315,285,"constant 20",["结果：%b : i32"],PURPLE)
    f.card(560,215,300,"arith.addi",["输入：%a、%b", "结果：%c : i32"],GREEN)
    f.card(1080,215,300,"func.return",["使用：%c"],ORANGE)
    f.arrow(345,205,550,260,"%a")
    f.arrow(345,380,550,310,"%b")
    f.arrow(870,290,1065,290,"%c")
    return f.save("lab00-ssa")


def memory(name, title, subtitle, blocks, note):
    f = Figure(title, subtitle, 390)
    width = 1240/len(blocks)
    for i,(label,base,size,detail) in enumerate(blocks):
        x=90+i*width
        f.rect(x,165,width-20,120,"#fff",COLORS[i])
        f.text(x+20,200,label,28,COLORS[i],weight="700")
        f.text(x+20,236,f"起点 {base} · 有效 {size} 字节",22)
        f.text(x+20,270,detail,20,GRAY)
        if i:
            f.arrow(x-20,145,x-20,159)
    f.text(720,333,note,22,GRAY,"middle")
    return f.save(name)


def matrix():
    f=Figure("Tiling：整矩阵变成可执行的小块", "M=5、N=6、K=7，tile-size=4。彩色区域是第一个分块。",600)
    def draw(x,y,rows,cols,label):
        size=43
        f.text(x,y-20,label,27,BLUE,weight="700")
        for r in range(rows):
            for c in range(cols):
                fill="#bbf7d0" if r<4 and c<4 else "#e2e8f0"
                f.rect(x+c*size,y+r*size,size-3,size-3,fill,"#fff",3)
        return x+cols*size
    draw(60,160,5,7,"A [5×7]")
    f.text(415,290,"×",42,GRAY)
    draw(485,160,7,6,"B [7×6]")
    f.text(805,290,"+ C →",31,GRAY)
    draw(970,160,5,6,"C [5×6]")
    f.text(720,520,"共 2 × 2 × 2 = 8 个 tile；尾块大小为 tm=1、tn=2、tk=3。",25,INK,"middle")
    return f.save("lab05-tiling")


def numberline():
    f=Figure("INT8 量化：把连续实数映射到离散格点", "示例 scale=0.5、zero point=0；每前进一个整数格，代表实数增加 0.5。",450)
    f.arrow(100,250,1340,250)
    for i in range(-3,4):
        x=720+i*180
        f.parts.append(f'<path d="M{x},238 v24" stroke="{BLUE}" stroke-width="3"/>')
        f.text(x,212,f"{i/2:g}",26,BLUE,"middle")
        f.text(x,303,f"q={i}",24,INK,"middle")
    f.text(720,365,"0.75 / 0.5 = 1.5 → 舍入到偶数 2 → 反量化为 1.0",25,INK,"middle")
    return f.save("lab05-quant-rounding")


def stages():
    f=Figure("项目有两条学习路线", "上方路线学习标量编译；下方路线学习 NPU 的计算、存储与整数执行。",600)
    for row, labels in enumerate([
        [("Toy",["Lab2 自定义算子"]),("Arith",["Lab3 完整转换"]),("LLVM Dialect",["Lab4 Lowering"]),("LLVM IR",["导出后由 lli 执行"])],
        [("Linalg",["完整矩阵乘加"]),("npu.matmul",["NPU 算子 IR"]),("npu.tile",["分块 + 地址属性"]),("NPU ISA",["伪指令 + 模拟器"])]]):
        y=150+row*215
        for i,(label,lines) in enumerate(labels):
            x=45+i*350
            f.card(x,y,300,label,lines,COLORS[i],145)
            if i:f.arrow(x-43,y+72,x-9,y+72)
    return f.save("learning-map")


def generate():
    OUT.mkdir(parents=True,exist_ok=True)
    paths=[stages(), nesting(), ssa(), matrix(), numberline()]
    flows=[
      ("lab00-build","从 C++ 源码到程序","配置阶段和编译阶段处理的是不同任务。",[("main.cpp","你写的源码"),("CMake","生成构建规则"),("Ninja + C++","编译并链接"),("my_program","可执行文件")],"修改源码后重新构建，才能运行到新行为。"),
      ("lab00-terminal","第一次打开项目","所有路径都以终端当前目录为起点。",[("pwd","查看当前目录"),("cd 项目路径","进入项目根目录"),("ls","查看有哪些文件"),("bash 脚本","开始构建和检查")],"$ 是常见提示符，不属于需要输入的命令。"),
      ("lab00-analysis-flow","MLIR C++ 程序如何读取 IR","分析程序先构建 IR 对象，再把 module 交给 Pass。",[("注册 Dialect","认识 arith / func"),("MLIRContext","管理 IR 上下文"),("parseSourceFile","文本 → IR"),("PassManager","调度分析 Pass"),("walk","找出每个 addi")],"分析程序输出统计信息，不会执行函数里的加法。"),
      ("lab01-pass-pattern","规则、Pass 和驱动器各自做什么","一个 Pattern 负责一个局部替换；驱动器负责多次尝试。",[("main","解析输入 IR"),("PassManager","安排 Pass"),("Simplify Pass","准备规则集合"),("Greedy Rewrite","维护工作列表"),("AddZeroPattern","匹配并替换")],"Pattern 匹配失败表示此规则不适用，通常不是整个编译失败。"),
      ("lab01-worklist","连续加零如何被处理","以下只展示一种可能的处理顺序，实际顺序不应成为代码假设。",[("%b = %a + 0","匹配右侧常量零"),("替换 %b","使用者自动改用 %a"),("%c = %a + 0","继续匹配下一条"),("return %a","没有 addi 残留")],"本例初始时两条加法就能匹配；它不证明必须多轮遍历。"),
      ("lab02-tablegen","TableGen 是生成 C++ 的工具",".td 是手写定义；.inc 是构建产物。",[("ToyOps.td","声明输入与结果"),("mlir-tblgen","生成声明和定义"),("ToyOps.*.inc","C++ 片段"),("C++ 编译器","构建 ToyDialect"),("toy-opt","解析自己的算子")],"不要修改 build/ 下的生成文件；重新构建会覆盖它们。"),
      ("lab02-register","从定义到注册","三处信息共同决定工具能否识别 toy.add。",[("Toy_Dialect","IR 前缀为 toy"),("Toy_AddOp","助记名为 add"),("addOperations","注册 Operation"),("registry.insert","让工具加载 Dialect")],"文本名称 toy.add，对应 C++ 类 mlir::toy::AddOp。"),
      ("lab02-builder","用 C++ 创建 IR","插入位置决定新 Operation 放在哪里。",[("ModuleOp","容纳函数"),("FuncOp","声明函数签名"),("Entry Block","设置插入位置"),("create<Op>","构造计算与 return"),("verify","检查结构和语义")],"OpBuilder 构造 IR；PatternRewriter 还负责通知重写驱动器。"),
      ("lab03-conversion","Full Conversion 的工作方式","转换既要有替换规则，也要满足最终合法性。",[("源 Toy IR","包含非法 Toy Op"),("ConversionTarget","定义哪些 Op 合法"),("Patterns + Types","替换和映射类型"),("Full Conversion","检查全部操作"),("Arith IR","不再含 Toy Op")],"没有更多规则能匹配，不代表剩余 IR 已经全部合法。"),
      ("lab04-pipeline","把多个 Pass 串成编译器","每一步读取前一步的 IR，并把结果交给后一步。",[("分析","统计 Toy 加法"),("Toy → Arith","替换算子"),("加零优化","删除 x + 0"),("Canonicalize","折叠常量"),("分析","核对优化结果")],"CSE 也在实际流水线中，用于合并公共子表达式。"),
      ("lab04-lowering","从 MLIR 走到可执行结果","LLVM Dialect 和 LLVM IR 是两个不同的表示。",[("Toy / Arith","MLIR 计算"),("LLVM Dialect","仍然是 MLIR"),("mlir-translate","导出文本"),("LLVM IR","program.ll"),("lli","运行，返回 30")],"返回值 30 来自 main；自动测试会把它当作预期结果。"),
      ("lab04-tests","测试链路","每一层都回答不同的问题。",[("CTest","统一测试入口"),("lit","读取 RUN 命令"),("FileCheck","核对输出 IR"),("lli + 检查脚本","核对执行结果")],"文本检查通过并不自动代表数值正确，所以还需要执行。"),
      ("lab05-ir-stages","Mini NPU 的三个 IR 阶段","npu.matmul 与 npu.tile 属于同一 Dialect，但抽象粒度不同。",[("Linalg IR","C += A × B"),("NPU 算子 IR","npu.matmul"),("NPU 分块 IR","npu.tile"),("地址属性","Memory Planning"),("伪指令","LOAD / MATMUL / STORE")],"地址规划增加属性；量化改变类型和 scale，都不单独新增一个方言。"),
      ("lab05-dma","一个 tile 如何执行","DRAM 保存完整矩阵，SRAM 保存这次计算所需的小块。",[("LOAD A/B","搬入输入小块"),("LOAD C","读取已有部分和"),("MATMUL","累加到 C tile"),("STORE C","把部分和写回"),("下一个 tile","重用 SRAM 区域")],"跨 K 分块必须保留 C；每次清零会丢失前面的结果。"),
      ("lab05-quant-pipeline","INT8 量化的完整流程","主机侧处理数据，编译器生成对应的整数 kernel。",[("真实 FP32 数据","校准 sA、sB"),("主机量化","A/B 为 INT8"),("编译 INT8 ABI","C 为 INT32"),("MATMUL_I8","有符号整数累加"),("反量化","输出 × sA × sB")],"仅改变 MLIR 类型不会自动改写外部 buffer 的实际数据。"),
    ]
    for args in flows: paths.append(flow(*args))
    comparisons=[
      ("lab00-source-build","源码目录与构建目录","把手写内容和自动生成内容分开，方便观察和重建。","源码目录",["main.cpp：程序内容","CMakeLists.txt：构建配置","README / TUTORIAL：学习材料"],"build/ 目录",["build.ninja：构建规则","*.o：编译中间结果","my_program：可执行文件"],"通常修改源码，不直接修改构建产物。"),
      ("lab01-replace","replaceOp 改的是使用关系","不需要按 SSA 名字搜索并手动修改后面的文本。","替换前",["%b = addi %a, %zero","%c = addi %b, %zero","return %c"],"替换 %b 之后",["第一条 addi 被删除","%c = addi %a, %zero","return %c"],"所有使用 %b 的地方自动改为使用 %a。"),
      ("lab01-match","哪些操作可以匹配","本实验只检查右操作数是不是可匹配的常量零。","匹配：执行替换",["%a + 常量 0 → %a","检查的是常量值","SSA 名字可以任意变化"],"不匹配：保持原样",["%a + 常量 20","常量 0 + 未知参数 %a","%a + 名字叫 %zero 的参数"],"名字相同不等于值相同；参数的运行时值通常未知。"),
      ("lab03-adaptor","为什么使用 Adaptor","转换后的加法应引用转换后常量的结果。","转换前的依赖",["toy.constant → %oldA","toy.constant → %oldB","toy.add(%oldA, %oldB)"],"转换后的依赖",["arith.constant → %newA","arith.constant → %newB","arith.addi(%newA, %newB)"],"adaptor.getLhs()/getRhs() 提供已重映射的操作数。"),
      ("lab03-types","这次 TypeConverter 为什么不改变类型","源 Toy 方言已经使用目标 Arith 能接受的内置整数类型。","当前：恒等映射",["i32 → i32","i64 → i64","函数签名无需改变"],"未来：改变类型",["例如 !toy.int → i32","需要处理块参数和函数签名","还可能需要 materialization"],"TypeConverter 描述类型映射，不会自动完成所有算子转换。"),
      ("lab04-cache","分析缓存何时可以重用","缓存是否有效，取决于中间的 Pass 是否修改相关 IR 并声明保留。","只读分析 Pass",["getAnalysis 获取统计","不改变 IR","markAllAnalysesPreserved"],"转换或重写 Pass",["改变 Operation 或使用关系","相关缓存失效","下次分析重新计算"],"不能把旧统计直接当作修改后 IR 的统计。"),
      ("lab05-quant-types","INT8 输入为什么配 INT32 输出","两个 8 位整数相乘并累加，结果通常无法放进 8 位。","FP32 kernel",["A：每元素 4 字节","B：每元素 4 字节","C：每元素 4 字节"],"INT8 kernel",["A：每元素 1 字节","B：每元素 1 字节","C：每元素仍为 4 字节"],"节省的是 A/B 数据量；C 保留足够的累加位宽。"),
      ("lab05-quant-error","两种正确性检查","整数实现正确，与相对原始浮点计算存在误差，可以同时成立。","整数参考检查",["输入同一份 qA / qB / qC","模拟 ISA 对比整数点积","应当逐元素完全一致"],"浮点误差检查",["qC_out × sA × sB","对比原始 FP32 计算","误差来自量化和舍入"],"同时报告整数精确一致和反量化误差，才能判断整条路径。"),
    ]
    for args in comparisons: paths.append(compare(*args))
    grids=[
      ("lab00-ir-vocabulary","读懂一条 arith.addi","%c = arith.addi %a, %b : i32",[("Operation","arith.addi 是一次加法操作","Operation 不是计算后的整数"),("Operand","%a 和 %b 是输入 Value","Value 连接定义者与使用者"),("Result","%c 是这个操作产生的 Value","一个 Op 可以有零个或多个结果"),("Type","i32 表示 32 位整数类型","Type 描述值的表示方式")]),
      ("lab02-op-parts","Operation 的定义由哪些部分组成","ODS 把约束、文本语法和 C++ API 联系起来。",[("arguments / results","声明输入、属性与结果","$lhs / $rhs / $result 决定访问器名称"),("Traits","例如 SameOperandsAndResultType","声明结构、类型或副作用相关性质"),("assemblyFormat","声明文本如何解析与打印","例如输入、逗号、冒号和结果类型"),("hasVerifier","生成 verify() 的声明","额外语义由手写 C++ 实现")]),
      ("lab02-verifier","合法性检查分两层","能解析成 IR，不代表满足这个 Dialect 的全部语义约束。",[("ODS 自动检查","输入和结果是不是整数类型","同一加法的三个类型是否一致"),("手写 Verifier","本方言只支持 i32 / i64","i16 即使是整数，也会被拒绝")]),
      ("lab03-legal","ConversionTarget 的合法性","Full Conversion 检查转换完成后的 Operation。",[("合法","Module、Func、Arith","可以在结果 IR 中保留"),("非法或未认可合法","Toy 必须转换，未知操作也不能残留","缺少转换规则时必须报告失败")]),
    ]
    for args in grids: paths.append(grid(*args))
    paths.append(memory("lab05-dram","FP32 DRAM 规划示例","图中每个框是一段 buffer 区域，框宽不按字节比例绘制。",[("A",0,140,"35 个 f32；下一区域从 192 开始"),("B",192,168,"42 个 f32；下一区域从 384 开始"),("C",384,120,"30 个 f32；保留初始值")],"64 字节对齐：地址 0、192、384，空隙是对齐填充。"))
    paths.append(memory("lab05-sram","一个 FP32 tile 的 SRAM 生命周期","4×4×4 tile：三个区域分别保存 A、B、C 小块。",[("A tile",0,64,"tm × tk × 4"),("B tile",64,64,"tk × tn × 4"),("C tile",128,64,"tm × tn × 4")],"当前 tile 完成写回后，这 192 字节可供下一个 tile 重用。"))
    paths.append(memory("lab05-int8-memory","INT8 DRAM：位宽变化会改变地址","仍使用 64 字节对齐。C 为 INT32，所以大小没有缩小。",[("A：INT8",0,35,"5 × 7 × 1"),("B：INT8",64,42,"7 × 6 × 1"),("C：INT32",128,120,"5 × 6 × 4")],"DMA 偏移必须乘以真实元素字节数，不能继续统一乘 4。"))
    return paths


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png",action="store_true")
    args=parser.parse_args()
    paths=generate()
    if args.png:
        import cairosvg
        for path in paths:
            cairosvg.svg2png(url=str(path),write_to=str(path.with_suffix(".png")))
    print(f"Generated {len(paths)} SVG diagrams" + (" and PNG copies" if args.png else ""))
