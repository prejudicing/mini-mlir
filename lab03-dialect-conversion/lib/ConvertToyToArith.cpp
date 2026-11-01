#include "ToyConversion.h"
#include "Toy/ToyOps.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/Pass/Pass.h"
#include "mlir/Transforms/DialectConversion.h"

using namespace mlir;
namespace {
struct ConvertConstant : OpConversionPattern<toy::ConstantOp> {
  using OpConversionPattern::OpConversionPattern;
  LogicalResult matchAndRewrite(toy::ConstantOp op, OpAdaptor adaptor,
      ConversionPatternRewriter &rewriter) const override {
    rewriter.replaceOpWithNewOp<arith::ConstantOp>(op,
        getTypeConverter()->convertType(op.getResult().getType()), adaptor.getValue());
    return success();
  }
};

struct ConvertAdd : OpConversionPattern<toy::AddOp> {
  using OpConversionPattern::OpConversionPattern;
  LogicalResult matchAndRewrite(toy::AddOp op, OpAdaptor adaptor,
      ConversionPatternRewriter &rewriter) const override {
    // adaptor 提供转换后并已重映射的操作数，而非原始 toy SSA Value。
    rewriter.replaceOpWithNewOp<arith::AddIOp>(op,
        adaptor.getLhs(), adaptor.getRhs());
    return success();
  }
};

struct ConvertToyToArithPass
    : PassWrapper<ConvertToyToArithPass, OperationPass<ModuleOp>> {
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(ConvertToyToArithPass)
  StringRef getArgument() const final { return "convert-toy-to-arith"; }
  StringRef getDescription() const final { return "Fully convert scalar Toy to Arith"; }
  void getDependentDialects(DialectRegistry &registry) const override {
    registry.insert<arith::ArithDialect>();
  }
  void runOnOperation() override {
    TypeConverter types;
    // 本方言已经使用内置 i32/i64，因此第一版类型转换是恒等映射。
    types.addConversion([](Type type) { return type; });
    RewritePatternSet patterns(&getContext());
    patterns.add<ConvertConstant, ConvertAdd>(types, &getContext());

    ConversionTarget target(getContext());
    target.addLegalOp<ModuleOp>();
    target.addLegalDialect<func::FuncDialect, arith::ArithDialect>();
    target.addIllegalDialect<toy::ToyDialect>();
    // 未声明合法的未知操作也无法通过 full conversion。
    if (failed(applyFullConversion(getOperation(), target, std::move(patterns))))
      signalPassFailure();
  }
};
} // namespace

std::unique_ptr<Pass> mlir::toy::createConvertToyToArithPass() {
  return std::make_unique<ConvertToyToArithPass>();
}
void mlir::toy::registerToyConversionPasses() {
  PassRegistration<ConvertToyToArithPass>();
}
