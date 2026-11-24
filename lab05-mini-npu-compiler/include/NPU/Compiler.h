#ifndef LEARNING_NPU_COMPILER_H
#define LEARNING_NPU_COMPILER_H
#include "mlir/Support/LogicalResult.h"
namespace llvm { class raw_ostream; }
namespace mlir {
class ModuleOp;
namespace npu {
// 将 Pass 与流水线名称登记到 MLIR 的命令行注册机制，不是注册到某个方言实例。
void registerNPUPasses();
// 显式发射接口：接收已规划模块，向指定输出流写伪指令。
LogicalResult emitInstructions(ModuleOp module, llvm::raw_ostream &output);
} // namespace npu
} // namespace mlir
#endif
