#include "NPU/NPU.h"
#include "NPU/Compiler.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/IR/Verifier.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Support/Format.h"
#include <algorithm>

using namespace mlir;
LogicalResult npu::emitInstructions(ModuleOp module, llvm::raw_ostream &output) {
  if (failed(verify(module))) return failure();
  // 先验证并生成到缓冲区，失败时不输出半份程序。
  std::string program;
  llvm::raw_string_ostream os(program);
  for (Operation &rawFunc : module.getBody()->getOperations()) {
    auto func = dyn_cast<func::FuncOp>(rawFunc);
    if (!func || func.isExternal() || func.getNumResults() ||
        func.getNumArguments() != 3 || !llvm::hasSingleElement(func.getBody()))
      return rawFunc.emitError("expected a planned NPU kernel function");
    if (failed(verifyMatrices(func, func.getArgument(0), func.getArgument(1), func.getArgument(2))))
      return failure();
    if (failed(verifyQuantization(func))) return failure();
    auto capacity = func->getAttrOfType<IntegerAttr>("npu.sram_capacity");
    auto declaredPeak = func->getAttrOfType<IntegerAttr>("npu.sram_bytes");
    if (!capacity || !declaredPeak || capacity.getInt() <= 0)
      return func.emitError("missing memory plan; run --npu-compile first");
    os << "FUNC " << func.getSymName() << " sram=" << declaredPeak.getInt() << '\n';
    if (func->hasAttr("npu.quantization"))
      os << "QUANT scheme=symmetric-per-tensor a_scale="
         << llvm::format("%.17g", func->getAttrOfType<FloatAttr>("npu.a_scale").getValueAsDouble())
         << " b_scale=" << llvm::format("%.17g", func->getAttrOfType<FloatAttr>("npu.b_scale").getValueAsDouble())
         << " c_scale=" << llvm::format("%.17g", func->getAttrOfType<FloatAttr>("npu.c_scale").getValueAsDouble()) << '\n';
    int64_t expectedAddress = 0;
    for (unsigned i = 0; i < func.getNumArguments(); ++i) {
      auto type = cast<MemRefType>(func.getArgument(i).getType());
      auto address = func.getArgAttrOfType<IntegerAttr>(i, "npu.address");
      auto bytes = func.getArgAttrOfType<IntegerAttr>(i, "npu.bytes");
      if (!address || !bytes || address.getInt() != expectedAddress ||
          bytes.getInt() != type.getNumElements() * elementBytes(type))
        return func.emitError("invalid or overlapping DRAM memory plan");
      os << "BUFFER id=" << i << " g=" << expectedAddress << " rows=" << type.getDimSize(0)
         << " cols=" << type.getDimSize(1) << " dtype="
         << (type.getElementType().isF32() ? "f32" : (elementBytes(type) == 1 ? "i8" : "i32")) << '\n';
      expectedAddress += align64(bytes.getInt());
    }
    int64_t peak = 0;
    for (Operation &raw : func.getBody().front()) {
      if (isa<func::ReturnOp>(raw)) continue;
      auto op = dyn_cast<TileOp>(raw);
      if (!op) return raw.emitError("instruction emission requires planned npu.tile operations");
      if (op.getA() != func.getArgument(0) || op.getB() != func.getArgument(1) ||
          op.getC() != func.getArgument(2))
        return op.emitError("buffers must follow the kernel A, B, C argument order");
      int64_t tm = op.getTmAttr().getInt(), tn = op.getTnAttr().getInt(), tk = op.getTkAttr().getInt();
      int64_t widths[3] = {elementBytes(cast<MemRefType>(op.getA().getType())),
                           elementBytes(cast<MemRefType>(op.getB().getType())),
                           elementBytes(cast<MemRefType>(op.getC().getType()))};
      int64_t bs = align64(tm * tk * widths[0]), cs = bs + align64(tk * tn * widths[1]);
      int64_t required = cs + align64(tm * tn * widths[2]);
      auto aSram = op->getAttrOfType<IntegerAttr>("a_sram");
      auto bSram = op->getAttrOfType<IntegerAttr>("b_sram");
      auto cSram = op->getAttrOfType<IntegerAttr>("c_sram");
      if (!aSram || !bSram || !cSram || aSram.getInt() != 0 ||
          bSram.getInt() != bs || cSram.getInt() != cs || required > capacity.getInt())
        return op.emitError("invalid or overlapping SRAM memory plan");
      peak = std::max(peak, required);

      int64_t offsets[3] = {op.getMAttr().getInt(), op.getKAttr().getInt(), op.getMAttr().getInt()};
      int64_t columns[3] = {op.getKAttr().getInt(), op.getNAttr().getInt(), op.getNAttr().getInt()};
      int64_t rows[3] = {tm, tk, tm}, cols[3] = {tk, tn, tn};
      int64_t sram[3] = {0, bs, cs}, global[3], strides[3];
      unsigned index = 0;
      for (Value value : {op.getA(), op.getB(), op.getC()}) {
        auto arg = dyn_cast<BlockArgument>(value);
        if (!arg || arg.getOwner() != &func.getBody().front())
          return op.emitError("NPU operands must be kernel arguments");
        auto type = cast<MemRefType>(arg.getType());
        strides[index] = type.getDimSize(1);
        int64_t base = func.getArgAttrOfType<IntegerAttr>(arg.getArgNumber(), "npu.address").getInt();
        global[index] = base + (offsets[index] * strides[index] + columns[index]) * widths[index];
        os << "LOAD2D g=" << global[index] << " s=" << sram[index]
           << " rows=" << rows[index] << " cols=" << cols[index] << " stride=" << strides[index]
           << " bytes=" << widths[index] << '\n';
        ++index;
      }
      // C tile 每个 K 分块先加载旧值，完成累加后写回，保留 C += A*B 语义。
      os << (widths[0] == 1 ? "MATMUL_I8" : "MATMUL")
         << " a=0 b=" << bs << " c=" << cs << " m=" << tm << " n=" << tn << " k=" << tk << '\n';
      os << "STORE2D s=" << cs << " g=" << global[2] << " rows=" << tm
         << " cols=" << tn << " stride=" << strides[2] << " bytes=" << widths[2] << '\n';
    }
    if (peak != declaredPeak.getInt()) return func.emitError("incorrect peak SRAM usage");
    os << "END\n";
  }
  output << program;
  return success();
}
