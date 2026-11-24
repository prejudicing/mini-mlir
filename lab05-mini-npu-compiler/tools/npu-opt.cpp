#include "NPU/NPU.h"
#include "NPU/Compiler.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/Dialect/Linalg/IR/Linalg.h"
#include "mlir/Tools/mlir-opt/MlirOptMain.h"

int main(int argc, char **argv) {
  // 方言注册让解析器认识 IR；Pass 注册让命令行认识 --npu-compile 等选项。
  mlir::DialectRegistry registry;
  registry.insert<mlir::npu::NPUDialect, mlir::linalg::LinalgDialect,
                  mlir::arith::ArithDialect, mlir::func::FuncDialect>();
  mlir::npu::registerNPUPasses();
  // 标准驱动器处理命令行、解析、运行 Pass 和打印 IR，本入口不执行矩阵计算。
  return mlir::asMainReturnCode(
      mlir::MlirOptMain(argc, argv, "Mini NPU compiler\n", registry));
}
