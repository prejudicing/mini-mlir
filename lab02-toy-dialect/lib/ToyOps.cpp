#include "Toy/ToyOps.h"
#include "mlir/IR/Builders.h"

#define GET_OP_CLASSES
#include "ToyOps.cpp.inc"

namespace mlir::toy {

// ODS 已保证 signless integer；手写 Verifier 再限制本方言支持的位宽。
static LogicalResult verifySupportedWidth(Operation *op, Type type) {
  if (!type.isSignlessInteger(32) && !type.isSignlessInteger(64))
    return op->emitOpError("only supports scalar i32 or i64, got ") << type;
  return success();
}

LogicalResult ConstantOp::verify() {
  // AllTypesMatch 已验证 value 属性类型与结果类型一致。
  return verifySupportedWidth(getOperation(), getResult().getType());
}

LogicalResult AddOp::verify() {
  // SameOperandsAndResultType 已验证 lhs、rhs、result 的类型一致。
  return verifySupportedWidth(getOperation(), getResult().getType());
}

} // namespace mlir::toy
