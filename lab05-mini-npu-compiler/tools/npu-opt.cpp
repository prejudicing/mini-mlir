#include "NPU/NPU.h"
#include "NPU/Compiler.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/Dialect/Linalg/IR/Linalg.h"
#include "mlir/Tools/mlir-opt/MlirOptMain.h"

int main(int argc, char **argv) {
  mlir::DialectRegistry registry;
  registry.insert<mlir::npu::NPUDialect, mlir::linalg::LinalgDialect,
                  mlir::arith::ArithDialect, mlir::func::FuncDialect>();
  mlir::npu::registerNPUPasses();
  return mlir::asMainReturnCode(
      mlir::MlirOptMain(argc, argv, "Mini NPU compiler\n", registry));
}
