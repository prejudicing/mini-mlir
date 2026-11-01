#include "Toy/ToyDialect.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/IR/DialectRegistry.h"
#include "mlir/Tools/mlir-opt/MlirOptMain.h"

int main(int argc, char **argv) {
  mlir::DialectRegistry registry;
  registry.insert<mlir::toy::ToyDialect, mlir::func::FuncDialect>();
  // 使用标准 opt 驱动器，获得解析、验证、打印及诊断检查等能力。
  return mlir::asMainReturnCode(
      mlir::MlirOptMain(argc, argv, "Toy dialect learning tool\n", registry));
}
