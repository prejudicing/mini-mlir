#include "NPU/NPU.h"
#include "mlir/IR/Builders.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include <algorithm>
#include <cmath>
#include <limits>

// TableGen 生成方言基础实现；GET_OP_CLASSES 选择生成文件中的 Op 类实现部分。
#include "NPUDialect.cpp.inc"
#define GET_OP_CLASSES
#include "NPUOps.cpp.inc"

using namespace mlir;
// 加载方言时框架调用 initialize；GET_OP_LIST 展开为 MatmulOp、TileOp 类型列表。
void npu::NPUDialect::initialize() {
  addOperations<
#define GET_OP_LIST
#include "NPUOps.cpp.inc"
      >();
}

// 所有阶段共用的矩阵约束：静态二维、连续行优先、约定的类型和形状。
LogicalResult npu::verifyMatrices(Operation *op, Value a, Value b, Value c) {
  for (Value value : {a, b, c}) {
    auto type = dyn_cast<MemRefType>(value.getType());
    if (!type || type.getRank() != 2 || !type.hasStaticShape() ||
        !type.getLayout().isIdentity() ||
        type.getMemorySpaceAsInt() != 0)
      return op->emitOpError("requires static rank-2 row-major memrefs in memory space 0");
    for (int64_t dim : type.getShape())
      if (dim <= 0 || dim > 4096)
        return op->emitOpError("matrix dimensions must be in [1, 4096]");
  }
  auto at = cast<MemRefType>(a.getType());
  auto bt = cast<MemRefType>(b.getType());
  auto ct = cast<MemRefType>(c.getType());
  bool fp32 = at.getElementType().isF32() && bt.getElementType().isF32() && ct.getElementType().isF32();
  // MLIR 的 signless i8 本身不指定符号；本项目的运算语义将它解释为有符号数。
  bool int8 = at.getElementType().isSignlessInteger(8) &&
              bt.getElementType().isSignlessInteger(8) && ct.getElementType().isSignlessInteger(32);
  if (!fp32 && !int8)
    return op->emitOpError("requires element types f32/f32/f32 or signed i8/i8/i32");
  if (at.getDimSize(1) != bt.getDimSize(0) ||
      at.getDimSize(0) != ct.getDimSize(0) || bt.getDimSize(1) != ct.getDimSize(1))
    return op->emitOpError("requires A[M,K], B[K,N], C[M,N]");
  // 这里只拒绝同一个 SSA buffer；不能证明不同参数在真实内存中不重叠。
  // 调用者还必须遵守 A/B/C 独立存储的 ABI。
  if (a == c || b == c)
    return op->emitOpError("output must not alias an input SSA buffer");
  return success();
}

// 只验证量化元数据的一致性，无法读取 buffer 数据来检查它是否已真正量化。
LogicalResult npu::verifyQuantization(Operation *function) {
  auto func = dyn_cast<func::FuncOp>(function);
  if (!func) return function->emitError("quantization metadata requires func.func");
  bool any = func->hasAttr("npu.a_scale") || func->hasAttr("npu.b_scale") ||
             func->hasAttr("npu.c_scale") || func->hasAttr("npu.quantization");
  if (!any) return success(); // 原生整数输入可以没有浮点量化元数据。
  auto scheme = func->getAttrOfType<StringAttr>("npu.quantization");
  auto a = func->getAttrOfType<FloatAttr>("npu.a_scale");
  auto b = func->getAttrOfType<FloatAttr>("npu.b_scale");
  auto c = func->getAttrOfType<FloatAttr>("npu.c_scale");
  if (!scheme || scheme.getValue() != "symmetric-per-tensor" || !a || !b || !c ||
      !a.getType().isF64() || !b.getType().isF64() || !c.getType().isF64())
    return func.emitError("requires symmetric-per-tensor metadata with three f64 scales");
  double av = a.getValueAsDouble(), bv = b.getValueAsDouble(), cv = c.getValueAsDouble();
  double product = av * bv;
  // 手写十进制属性（例如 .1 * .2 与 .02）允许正常的 f64 舍入差异。
  if (!std::isfinite(av) || !std::isfinite(bv) || !std::isfinite(cv) ||
      av <= 0 || bv <= 0 || cv <= 0 || !std::isfinite(product) || product <= 0 ||
      std::abs(cv - product) > 4 * std::numeric_limits<double>::epsilon() * std::max(cv, product))
    return func.emitError("quantization scales must be finite and positive, with c_scale = a_scale * b_scale");
  if (func.getNumArguments() != 3) return func.emitError("quantization requires three buffers");
  for (unsigned i = 0; i < 3; ++i) {
    auto type = dyn_cast<MemRefType>(func.getArgument(i).getType());
    if (!type || !type.getElementType().isSignlessInteger(i == 2 ? 32 : 8))
      return func.emitError("quantization metadata requires i8/i8/i32 buffers");
  }
  return success();
}

LogicalResult npu::MatmulOp::verify() {
  return verifyMatrices(getOperation(), getA(), getB(), getC());
}

// tile 同时引用完整矩阵和块的偏移/尺寸；以“剩余大小”检查边界，避免加法溢出。
LogicalResult npu::TileOp::verify() {
  if (failed(verifyMatrices(getOperation(), getA(), getB(), getC()))) return failure();
  auto at = cast<MemRefType>(getA().getType());
  auto ct = cast<MemRefType>(getC().getType());
  int64_t m = getMAttr().getInt(), n = getNAttr().getInt(), k = getKAttr().getInt();
  int64_t tm = getTmAttr().getInt(), tn = getTnAttr().getInt(), tk = getTkAttr().getInt();
  if (m < 0 || n < 0 || k < 0 || tm <= 0 || tn <= 0 || tk <= 0 ||
      m >= ct.getDimSize(0) || n >= ct.getDimSize(1) || k >= at.getDimSize(1) ||
      tm > ct.getDimSize(0) - m || tn > ct.getDimSize(1) - n || tk > at.getDimSize(1) - k)
    return emitOpError("tile offsets/sizes are out of matrix bounds");
  return success();
}
