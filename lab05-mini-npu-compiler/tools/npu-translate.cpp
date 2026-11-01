#include "NPU/NPU.h"
#include "NPU/Compiler.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/IR/MLIRContext.h"
#include "mlir/Parser/Parser.h"
#include "llvm/Support/raw_ostream.h"

int main(int argc, char **argv) {
  if (argc != 2) {
    llvm::errs() << "Usage: " << argv[0] << " <planned.mlir | ->\n";
    return 1;
  }
  mlir::DialectRegistry registry;
  registry.insert<mlir::npu::NPUDialect, mlir::func::FuncDialect>();
  mlir::MLIRContext context(registry);
  auto module = mlir::parseSourceFile<mlir::ModuleOp>(argv[1], &context);
  if (!module) return 1;
  return mlir::failed(mlir::npu::emitInstructions(*module, llvm::outs())) ? 1 : 0;
}
