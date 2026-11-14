#include "Toy/ToyDialect.h"
#include "Toy/ToyOps.h"

#include "ToyDialect.cpp.inc"

void mlir::toy::ToyDialect::initialize() {
  // TODO(LAB2-MUL-3)：完成 MulOp 后，检查重新生成的 GET_OP_LIST 分支。
  // 确认其中包含 mlir::toy::MulOp，并解释它如何经 addOperations 注册。
  // 此处通常不需要增加手写类名；请不要修改生成文件来完成注册。
  // GET_OP_LIST 将生成文件展开为 ConstantOp、AddOp 的类型列表。
  addOperations<
#define GET_OP_LIST
#include "ToyOps.cpp.inc"
      >();
}
