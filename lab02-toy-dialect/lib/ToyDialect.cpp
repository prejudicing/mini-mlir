#include "Toy/ToyDialect.h"
#include "Toy/ToyOps.h"

#include "ToyDialect.cpp.inc"

void mlir::toy::ToyDialect::initialize() {
  // GET_OP_LIST 将生成文件展开为 ConstantOp、AddOp 的类型列表。
  addOperations<
#define GET_OP_LIST
#include "ToyOps.cpp.inc"
      >();
}
