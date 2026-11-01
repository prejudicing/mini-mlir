#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/IR/DialectRegistry.h"
#include "mlir/IR/MLIRContext.h"
#include "mlir/IR/Matchers.h"
#include "mlir/IR/PatternMatch.h"
#include "mlir/Parser/Parser.h"
#include "mlir/Pass/Pass.h"
#include "mlir/Pass/PassManager.h"
#include "mlir/Transforms/GreedyPatternRewriteDriver.h"
#include "llvm/Support/raw_ostream.h"

#include <memory>
#include <utility>

using namespace mlir;

namespace {

// Pattern 只描述局部规则；遍历和重复应用由 Greedy Rewrite 驱动器负责。
struct AddZeroPattern : public OpRewritePattern<arith::AddIOp> {
  using OpRewritePattern<arith::AddIOp>::OpRewritePattern;

  LogicalResult matchAndRewrite(arith::AddIOp op,
                                PatternRewriter &rewriter) const override {
    // 检查 RHS 的实际常量值，与 SSA 名称是否叫 %zero 无关。
    if (!matchPattern(op.getRhs(), m_Zero()))
      return failure();

    // 将结果的所有使用替换成 LHS，并删除当前 addi。
    // 必须通过 rewriter 修改 IR，让驱动器正确更新工作列表。
    rewriter.replaceOp(op, op.getLhs());
    return success();
  }
};

struct SimplifyAddZeroPass
    : public PassWrapper<SimplifyAddZeroPass, OperationPass<ModuleOp>> {
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(SimplifyAddZeroPass)

  StringRef getArgument() const final { return "simplify-add-zero"; }
  StringRef getDescription() const final { return "Rewrite integer x + 0 to x"; }

  void runOnOperation() override {
    RewritePatternSet patterns(&getContext());
    patterns.add<AddZeroPattern>(&getContext());

    GreedyRewriteConfig config;
    // 隔离本实验的 Pattern 效果：避免内置 folding 将 10 + 20 变成 30。
    config.fold = false;

    FrozenRewritePatternSet frozenPatterns(std::move(patterns));
    if (failed(applyPatternsGreedily(getOperation(), frozenPatterns, config)))
      signalPassFailure();
  }
};

} // namespace

int main(int argc, char **argv) {
  if (argc != 2) {
    llvm::errs() << "Usage: " << argv[0] << " <input.mlir>\n";
    return 1;
  }

  DialectRegistry registry;
  registry.insert<arith::ArithDialect, func::FuncDialect>();
  MLIRContext context(registry);

  auto module = parseSourceFile<ModuleOp>(argv[1], &context);
  if (!module) {
    llvm::errs() << "Failed to parse input MLIR\n";
    return 1;
  }

  PassManager pm(&context);
  pm.enableVerifier(true);
  pm.addPass(std::make_unique<SimplifyAddZeroPass>());
  if (failed(pm.run(*module))) {
    llvm::errs() << "Pass execution failed\n";
    return 1;
  }

  module->print(llvm::outs());
  llvm::outs() << '\n';
  return 0;
}
