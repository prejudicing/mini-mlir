#include "ToyConversion.h"
#include "Toy/ToyDialect.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/Tools/mlir-opt/MlirOptMain.h"

int main(int argc, char **argv) {
  mlir::DialectRegistry registry;
  registry.insert<mlir::toy::ToyDialect, mlir::arith::ArithDialect,
                  mlir::func::FuncDialect>();
  mlir::toy::registerToyConversionPasses();
  return mlir::asMainReturnCode(
      mlir::MlirOptMain(argc, argv, "Lab3: Toy to Arith\n", registry));
}
