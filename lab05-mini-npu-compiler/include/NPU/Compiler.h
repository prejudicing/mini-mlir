#ifndef LEARNING_NPU_COMPILER_H
#define LEARNING_NPU_COMPILER_H
#include "mlir/Support/LogicalResult.h"
namespace llvm { class raw_ostream; }
namespace mlir {
class ModuleOp;
namespace npu {
void registerNPUPasses();
LogicalResult emitInstructions(ModuleOp module, llvm::raw_ostream &output);
} // namespace npu
} // namespace mlir
#endif
