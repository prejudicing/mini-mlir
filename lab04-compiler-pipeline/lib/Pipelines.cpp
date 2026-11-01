#include "Pipelines.h"
#include "ToyConversion.h"
#include "mlir/Conversion/ArithToLLVM/ArithToLLVM.h"
#include "mlir/Conversion/FuncToLLVM/ConvertFuncToLLVMPass.h"
#include "mlir/Conversion/ReconcileUnrealizedCasts/ReconcileUnrealizedCasts.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/IR/Matchers.h"
#include "mlir/IR/PatternMatch.h"
#include "mlir/Pass/Pass.h"
#include "mlir/Pass/PassManager.h"
#include "mlir/Pass/PassRegistry.h"
#include "mlir/Transforms/GreedyPatternRewriteDriver.h"
#include "mlir/Transforms/Passes.h"
#include "llvm/Support/raw_ostream.h"

using namespace mlir;
namespace {
// 分析对象按需计算；不修改 IR 时可以在多个 Pass 之间缓存。
struct OperationCounts {
  explicit OperationCounts(Operation *root) {
    root->walk([&](Operation *op) {
      ++total;
      if (op->getName().getStringRef() == "toy.add") ++toyAdds;
      if (isa<arith::AddIOp>(op)) ++arithAdds;
    });
  }
  unsigned total = 0, toyAdds = 0, arithAdds = 0;
};

struct AnalyzePass : PassWrapper<AnalyzePass, OperationPass<ModuleOp>> {
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(AnalyzePass)
  StringRef getArgument() const final { return "lab4-analyze"; }
  StringRef getDescription() const final { return "Report cached operation counts"; }
  void runOnOperation() override {
    const auto &counts = getAnalysis<OperationCounts>();
    llvm::errs() << "[lab4-analysis] total=" << counts.total
                 << " toy.add=" << counts.toyAdds
                 << " arith.addi=" << counts.arithAdds << '\n';
    markAllAnalysesPreserved();
  }
};

struct AddZero : OpRewritePattern<arith::AddIOp> {
  using OpRewritePattern::OpRewritePattern;
  LogicalResult matchAndRewrite(arith::AddIOp op,
                                PatternRewriter &rewriter) const override {
    if (!matchPattern(op.getRhs(), m_Zero())) return failure();
    rewriter.replaceOp(op, op.getLhs());
    return success();
  }
};

struct SimplifyPass : PassWrapper<SimplifyPass, OperationPass<func::FuncOp>> {
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(SimplifyPass)
  StringRef getArgument() const final { return "lab4-simplify-add-zero"; }
  StringRef getDescription() const final { return "Apply Lab1 rule inside each function"; }
  void runOnOperation() override {
    RewritePatternSet patterns(&getContext());
    patterns.add<AddZero>(&getContext());
    GreedyRewriteConfig config;
    config.fold = false;
    if (failed(applyPatternsGreedily(getOperation(),
        FrozenRewritePatternSet(std::move(patterns)), config))) signalPassFailure();
  }
};

void buildOptimizePipeline(OpPassManager &pm) {
  pm.addPass(std::make_unique<AnalyzePass>());
  pm.addPass(toy::createConvertToyToArithPass());
  pm.addNestedPass<func::FuncOp>(std::make_unique<SimplifyPass>());
  pm.addPass(createCanonicalizerPass());
  pm.addPass(createCSEPass());
  pm.addPass(std::make_unique<AnalyzePass>());
}
} // namespace

void registerLab4Pipelines() {
  toy::registerToyConversionPasses();
  PassRegistration<AnalyzePass>();
  PassRegistration<SimplifyPass>();
  PassPipelineRegistration<>("lab4-optimize", "Toy conversion and scalar optimization",
      [](OpPassManager &pm) { buildOptimizePipeline(pm); });
  PassPipelineRegistration<>("lab4-lower-to-llvm", "Optimize Toy and lower to LLVM dialect",
      [](OpPassManager &pm) {
        buildOptimizePipeline(pm);
        pm.addPass(createArithToLLVMConversionPass());
        pm.addPass(createConvertFuncToLLVMPass());
        pm.addPass(createReconcileUnrealizedCastsPass());
      });
}
