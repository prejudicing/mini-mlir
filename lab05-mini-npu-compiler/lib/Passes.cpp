#include "NPU/NPU.h"
#include "NPU/Compiler.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/Dialect/Linalg/IR/Linalg.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/IR/PatternMatch.h"
#include "mlir/Pass/Pass.h"
#include "mlir/Pass/PassManager.h"
#include "mlir/Pass/PassRegistry.h"
#include "mlir/Transforms/DialectConversion.h"
#include <algorithm>
#include <cmath>

using namespace mlir;
namespace {
LogicalResult verifyFunction(func::FuncOp func) {
  if (func.isExternal() || func.getNumResults() || !llvm::hasSingleElement(func.getBody()) ||
      func.getNumArguments() != 3)
    return func.emitOpError("NPU kernels require one block, three buffers, no results and a body");
  if (failed(npu::verifyMatrices(func, func.getArgument(0), func.getArgument(1), func.getArgument(2))))
    return failure();
  return npu::verifyQuantization(func);
}

struct LowerMatmul : OpConversionPattern<linalg::MatmulOp> {
  using OpConversionPattern::OpConversionPattern;
  LogicalResult matchAndRewrite(linalg::MatmulOp op, OpAdaptor adaptor,
      ConversionPatternRewriter &rewriter) const override {
    if (op.getNumResults() || op.getInputs().size() != 2 || op.getOutputs().size() != 1)
      return rewriter.notifyMatchFailure(op, "only buffer semantics are supported");
    if (op.getCast() != linalg::TypeFn::cast_signed)
      return rewriter.notifyMatchFailure(op, "only signed operand extension is supported");
    // 拒绝转置/广播等自定义 indexing_maps，避免悄悄改变矩阵语义。
    auto maps = op.getIndexingMapsArray();
    MLIRContext *ctx = op.getContext();
    auto d0 = getAffineDimExpr(0, ctx), d1 = getAffineDimExpr(1, ctx), d2 = getAffineDimExpr(2, ctx);
    SmallVector<AffineMap> expected = {
      AffineMap::get(3, 0, {d0, d2}, ctx), AffineMap::get(3, 0, {d2, d1}, ctx),
      AffineMap::get(3, 0, {d0, d1}, ctx)};
    if (maps != expected)
      return rewriter.notifyMatchFailure(op, "only standard matmul indexing maps are supported");
    Value a = adaptor.getInputs()[0], b = adaptor.getInputs()[1], c = adaptor.getOutputs()[0];
    auto func = op->getParentOfType<func::FuncOp>();
    if (!func || a != func.getArgument(0) || b != func.getArgument(1) || c != func.getArgument(2))
      return rewriter.notifyMatchFailure(op, "buffers must follow the kernel A, B, C argument order");
    if (failed(npu::verifyMatrices(op, a, b, c))) return failure();
    rewriter.replaceOpWithNewOp<npu::MatmulOp>(op, a, b, c);
    return success();
  }
};

struct LowerPass : PassWrapper<LowerPass, OperationPass<ModuleOp>> {
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(LowerPass)
  StringRef getArgument() const final { return "convert-linalg-to-npu"; }
  StringRef getDescription() const final { return "Lower buffer matmul to NPU"; }
  void getDependentDialects(DialectRegistry &registry) const override {
    registry.insert<npu::NPUDialect>();
  }
  void runOnOperation() override {
    for (auto func : getOperation().getOps<func::FuncOp>())
      if (failed(verifyFunction(func))) return signalPassFailure();
    RewritePatternSet patterns(&getContext());
    patterns.add<LowerMatmul>(&getContext());
    ConversionTarget target(getContext());
    target.addLegalOp<ModuleOp>();
    target.addLegalDialect<func::FuncDialect, npu::NPUDialect>();
    target.addIllegalDialect<linalg::LinalgDialect>();
    if (failed(applyFullConversion(getOperation(), target, std::move(patterns)))) signalPassFailure();
  }
};

// 改变 kernel ABI：调用者必须先按这些 scale 真正量化数据，不能传入原始 float 字节。
struct QuantizePass : PassWrapper<QuantizePass, OperationPass<ModuleOp>> {
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(QuantizePass)
  QuantizePass() = default;
  QuantizePass(const QuantizePass &other) : PassWrapper(other) {}
  QuantizePass(double a, double b) { aScale = a; bScale = b; }
  Option<double> aScale{*this, "a-scale", llvm::cl::desc("Positive A quantization scale"), llvm::cl::init(1.0)};
  Option<double> bScale{*this, "b-scale", llvm::cl::desc("Positive B quantization scale"), llvm::cl::init(1.0)};
  StringRef getArgument() const final { return "npu-quantize-int8"; }
  StringRef getDescription() const final { return "Quantize an untiled f32 NPU kernel ABI to i8/i8/i32"; }
  void runOnOperation() override {
    double product = aScale * bScale;
    if (!std::isfinite(aScale) || !std::isfinite(bScale) || aScale <= 0 || bScale <= 0 ||
        !std::isfinite(product) || product <= 0) {
      getOperation().emitError("a-scale, b-scale and their product must be finite and positive");
      return signalPassFailure();
    }
    // 在改变任何类型前验证整个模块，避免半量化与重复量化。
    for (auto func : getOperation().getOps<func::FuncOp>()) {
      if (failed(verifyFunction(func))) return signalPassFailure();
      for (Value arg : func.getArguments())
        if (!cast<MemRefType>(arg.getType()).getElementType().isF32()) {
          func.emitError("INT8 quantization requires an unquantized f32 kernel");
          return signalPassFailure();
        }
      for (Operation &op : func.getBody().front()) {
        if (!isa<npu::MatmulOp, func::ReturnOp>(op)) {
          op.emitError("quantization must run after NPU lowering and before tiling");
          return signalPassFailure();
        }
        if (auto matmul = dyn_cast<npu::MatmulOp>(op))
          if (matmul.getA() != func.getArgument(0) || matmul.getB() != func.getArgument(1) ||
              matmul.getC() != func.getArgument(2)) {
            op.emitError("buffers must follow the kernel A, B, C argument order");
            return signalPassFailure();
          }
      }
    }
    Builder builder(&getContext());
    for (auto func : getOperation().getOps<func::FuncOp>()) {
      SmallVector<Type> inputs;
      for (unsigned i = 0; i < 3; ++i) {
        auto old = cast<MemRefType>(func.getArgument(i).getType());
        auto type = MemRefType::get(old.getShape(), builder.getIntegerType(i == 2 ? 32 : 8));
        func.getArgument(i).setType(type);
        inputs.push_back(type);
        // ABI 变化后不能保留可能已经过时的内存规划属性。
        func.removeArgAttr(i, "npu.address");
        func.removeArgAttr(i, "npu.bytes");
      }
      func.setType(builder.getFunctionType(inputs, {}));
      func->removeAttr("npu.sram_bytes");
      func->removeAttr("npu.sram_capacity");
      func->setAttr("npu.quantization", builder.getStringAttr("symmetric-per-tensor"));
      func->setAttr("npu.a_scale", builder.getF64FloatAttr(aScale));
      func->setAttr("npu.b_scale", builder.getF64FloatAttr(bScale));
      func->setAttr("npu.c_scale", builder.getF64FloatAttr(product));
    }
  }
};

struct TilePass : PassWrapper<TilePass, OperationPass<ModuleOp>> {
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(TilePass)
  TilePass() = default;
  TilePass(const TilePass &other) : PassWrapper(other) {}
  explicit TilePass(int64_t size) { tileSize = size; }
  Option<int64_t> tileSize{*this, "tile-size", llvm::cl::desc("M/N/K tile size"), llvm::cl::init(4)};
  StringRef getArgument() const final { return "npu-tile"; }
  StringRef getDescription() const final { return "Tile NPU matmul with boundary handling"; }
  void runOnOperation() override {
    if (tileSize < 1 || tileSize > 64) {
      getOperation().emitError("tile-size must be in [1, 64]");
      return signalPassFailure();
    }
    SmallVector<npu::MatmulOp> matmuls;
    getOperation().walk([&](npu::MatmulOp op) { matmuls.push_back(op); });
    IRRewriter rewriter(&getContext());
    for (auto op : matmuls) {
      auto at = cast<MemRefType>(op.getA().getType());
      auto ct = cast<MemRefType>(op.getC().getType());
      int64_t M = ct.getDimSize(0), N = ct.getDimSize(1), K = at.getDimSize(1);
      if (((M + tileSize - 1) / tileSize) * ((N + tileSize - 1) / tileSize) *
          ((K + tileSize - 1) / tileSize) > 100000) {
        op.emitError("tiling would exceed 100000 instructions; use larger tiles");
        return signalPassFailure();
      }
      rewriter.setInsertionPoint(op);
      for (int64_t m = 0; m < M; m += tileSize)
        for (int64_t n = 0; n < N; n += tileSize)
          for (int64_t k = 0; k < K; k += tileSize)
            rewriter.create<npu::TileOp>(op.getLoc(), op.getA(), op.getB(), op.getC(),
              rewriter.getI64IntegerAttr(m), rewriter.getI64IntegerAttr(n), rewriter.getI64IntegerAttr(k),
              rewriter.getI64IntegerAttr(std::min<int64_t>(tileSize, M - m)),
              rewriter.getI64IntegerAttr(std::min<int64_t>(tileSize, N - n)),
              rewriter.getI64IntegerAttr(std::min<int64_t>(tileSize, K - k)));
      rewriter.eraseOp(op);
    }
  }
};

struct PlanPass : PassWrapper<PlanPass, OperationPass<ModuleOp>> {
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(PlanPass)
  PlanPass() = default;
  PlanPass(const PlanPass &other) : PassWrapper(other) {}
  explicit PlanPass(int64_t bytes) { capacity = bytes; }
  Option<int64_t> capacity{*this, "sram-bytes", llvm::cl::desc("SRAM capacity in bytes"), llvm::cl::init(4096)};
  StringRef getArgument() const final { return "npu-plan-memory"; }
  StringRef getDescription() const final { return "Assign aligned DRAM/SRAM addresses"; }
  void runOnOperation() override {
    if (capacity <= 0) {
      getOperation().emitError("sram-bytes must be positive");
      return signalPassFailure();
    }
    Builder builder(&getContext());
    for (auto func : getOperation().getOps<func::FuncOp>()) {
      if (failed(verifyFunction(func))) return signalPassFailure();
      int64_t address = 0, peak = 0;
      for (auto [index, arg] : llvm::enumerate(func.getArguments())) {
        auto type = cast<MemRefType>(arg.getType());
        int64_t bytes = type.getNumElements() * npu::elementBytes(type);
        func.setArgAttr(index, "npu.address", builder.getI64IntegerAttr(address));
        func.setArgAttr(index, "npu.bytes", builder.getI64IntegerAttr(bytes));
        address += npu::align64(bytes);
      }
      for (Operation &raw : func.getBody().front()) {
        if (isa<func::ReturnOp>(raw)) continue;
        auto op = dyn_cast<npu::TileOp>(raw);
        if (!op) {
          raw.emitError("memory planning requires only npu.tile and func.return");
          return signalPassFailure();
        }
        for (Value operand : {op.getA(), op.getB(), op.getC()})
          if (!isa<BlockArgument>(operand) || operand.getParentBlock() != &func.getBody().front()) {
            op.emitError("NPU buffers must be kernel arguments");
            return signalPassFailure();
          }
        if (op.getA() != func.getArgument(0) || op.getB() != func.getArgument(1) ||
            op.getC() != func.getArgument(2)) {
          op.emitError("buffers must follow the kernel A, B, C argument order");
          return signalPassFailure();
        }
        int64_t tm = op.getTmAttr().getInt(), tn = op.getTnAttr().getInt(), tk = op.getTkAttr().getInt();
        int64_t ab = npu::elementBytes(cast<MemRefType>(op.getA().getType()));
        int64_t bb = npu::elementBytes(cast<MemRefType>(op.getB().getType()));
        int64_t cb = npu::elementBytes(cast<MemRefType>(op.getC().getType()));
        int64_t b = npu::align64(tm * tk * ab);
        int64_t c = b + npu::align64(tk * tn * bb);
        int64_t required = c + npu::align64(tm * tn * cb);
        if (required > capacity) {
          op.emitError("tile exceeds SRAM capacity: requires ") << required << " bytes, available " << capacity.getValue();
          return signalPassFailure();
        }
        op->setAttr("a_sram", builder.getI64IntegerAttr(0));
        op->setAttr("b_sram", builder.getI64IntegerAttr(b));
        op->setAttr("c_sram", builder.getI64IntegerAttr(c));
        peak = std::max(peak, required);
      }
      // 每个 tile 同步执行，三个 scratch buffer 可在后续 tile 重用。
      func->setAttr("npu.sram_bytes", builder.getI64IntegerAttr(peak));
      func->setAttr("npu.sram_capacity", builder.getI64IntegerAttr(capacity));
    }
  }
};

struct PipelineOptions : PassPipelineOptions<PipelineOptions> {
  Option<int64_t> tileSize{*this, "tile-size", llvm::cl::desc("M/N/K tile size"), llvm::cl::init(4)};
  Option<int64_t> sramBytes{*this, "sram-bytes", llvm::cl::desc("SRAM capacity in bytes"), llvm::cl::init(4096)};
  Option<bool> quantizeInt8{*this, "quantize-int8", llvm::cl::desc("Quantize f32 kernels to signed i8/i8/i32"), llvm::cl::init(false)};
  Option<double> aScale{*this, "a-scale", llvm::cl::desc("A per-tensor scale"), llvm::cl::init(1.0)};
  Option<double> bScale{*this, "b-scale", llvm::cl::desc("B per-tensor scale"), llvm::cl::init(1.0)};
};
} // namespace

void mlir::npu::registerNPUPasses() {
  PassRegistration<LowerPass>();
  PassRegistration<QuantizePass>();
  PassRegistration<TilePass>();
  PassRegistration<PlanPass>();
  PassPipelineRegistration<PipelineOptions>("npu-compile", "Lower, tile and plan a static matmul kernel",
      [](OpPassManager &pm, const PipelineOptions &options) {
        pm.addPass(std::make_unique<LowerPass>());
        if (options.quantizeInt8)
          pm.addPass(std::make_unique<QuantizePass>(options.aScale, options.bScale));
        pm.addPass(std::make_unique<TilePass>(options.tileSize));
        pm.addPass(std::make_unique<PlanPass>(options.sramBytes));
      });
}
