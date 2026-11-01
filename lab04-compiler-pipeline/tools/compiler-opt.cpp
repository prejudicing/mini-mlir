#include "Pipelines.h"
#include "Toy/ToyDialect.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Tools/mlir-opt/MlirOptMain.h"

int main(int argc, char **argv) {
  mlir::DialectRegistry registry;
  registry.insert<mlir::toy::ToyDialect, mlir::arith::ArithDialect,
                  mlir::func::FuncDialect, mlir::LLVM::LLVMDialect>();
  registerLab4Pipelines();
  return mlir::asMainReturnCode(
      mlir::MlirOptMain(argc, argv, "Lab4: scalar compiler pipeline\n", registry));
}
