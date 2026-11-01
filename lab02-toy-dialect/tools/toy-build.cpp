#include "Toy/ToyOps.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/IR/Builders.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/IR/MLIRContext.h"
#include "mlir/IR/Verifier.h"
#include "llvm/Support/raw_ostream.h"

int main() {
  mlir::MLIRContext context;
  context.getOrLoadDialect<mlir::toy::ToyDialect>();
  context.getOrLoadDialect<mlir::func::FuncDialect>();
  mlir::OpBuilder builder(&context);
  auto loc = builder.getUnknownLoc();
  mlir::OwningOpRef<mlir::ModuleOp> module(mlir::ModuleOp::create(loc));

  builder.setInsertionPointToStart(module->getBody());
  auto function = builder.create<mlir::func::FuncOp>(
      loc, "main", builder.getFunctionType({}, {builder.getI32Type()}));
  builder.setInsertionPointToStart(function.addEntryBlock());

  // 使用 TableGen 生成的 builder：常量类型从属性推导，加法类型从操作数推导。
  auto a = builder.create<mlir::toy::ConstantOp>(loc, builder.getI32IntegerAttr(10));
  auto b = builder.create<mlir::toy::ConstantOp>(loc, builder.getI32IntegerAttr(20));
  auto sum = builder.create<mlir::toy::AddOp>(loc, a.getResult(), b.getResult());
  builder.create<mlir::func::ReturnOp>(loc, sum.getResult());

  // 创建 Operation 不会自动完成全部语义验证，显式调用 verify。
  if (mlir::failed(mlir::verify(*module)))
    return 1;
  module->print(llvm::outs());
  llvm::outs() << '\n';
  return 0;
}
