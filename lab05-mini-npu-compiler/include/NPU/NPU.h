#ifndef LEARNING_NPU_H
#define LEARNING_NPU_H
#include "mlir/Bytecode/BytecodeOpInterface.h"
#include "mlir/IR/BuiltinTypes.h"
#include "mlir/IR/Dialect.h"
#include "mlir/IR/OpDefinition.h"
#include "mlir/IR/OpImplementation.h"
// 手写头文件包住 TableGen 声明；生成文件在 build 中，不直接手改。
#include "NPUDialect.h.inc"
#define GET_OP_CLASSES
#include "NPUOps.h.inc"

namespace mlir::npu {
// 前端、Verifier、规划和发射共同使用的约束。
LogicalResult verifyMatrices(Operation *op, Value a, Value b, Value c);
LogicalResult verifyQuantization(Operation *function);
// inline 允许此头文件中的同一函数定义出现在多个编译单元，不保证一定内联展开。
inline int64_t elementBytes(MemRefType type) {
  return type.getElementType().getIntOrFloatBitWidth() / 8;
}
// 向上取整到 64 字节边界，供 DRAM 分区和 SRAM scratch 空间共同使用。
inline int64_t align64(int64_t bytes) { return (bytes + 63) / 64 * 64; }
} // namespace mlir::npu
#endif
