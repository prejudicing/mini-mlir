#ifndef LEARNING_NPU_H
#define LEARNING_NPU_H
#include "mlir/Bytecode/BytecodeOpInterface.h"
#include "mlir/IR/BuiltinTypes.h"
#include "mlir/IR/Dialect.h"
#include "mlir/IR/OpDefinition.h"
#include "mlir/IR/OpImplementation.h"
#include "NPUDialect.h.inc"
#define GET_OP_CLASSES
#include "NPUOps.h.inc"

namespace mlir::npu {
// 前端、Verifier、规划和发射共同使用的约束。
LogicalResult verifyMatrices(Operation *op, Value a, Value b, Value c);
LogicalResult verifyQuantization(Operation *function);
inline int64_t elementBytes(MemRefType type) {
  return type.getElementType().getIntOrFloatBitWidth() / 8;
}
inline int64_t align64(int64_t bytes) { return (bytes + 63) / 64 * 64; }
} // namespace mlir::npu
#endif
