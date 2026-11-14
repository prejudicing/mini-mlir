#ifndef TOY_OPS_TD
#define TOY_OPS_TD

include "Toy/ToyDialect.td"
include "mlir/IR/BuiltinAttributeInterfaces.td"
include "mlir/Interfaces/InferTypeOpInterface.td"
include "mlir/Interfaces/SideEffectInterfaces.td"

class Toy_Op<string mnemonic, list<Trait> traits = []>
    : Op<Toy_Dialect, mnemonic, traits>;

def Toy_ConstantOp : Toy_Op<"constant", [Pure,
    AllTypesMatch<["value", "result"]>]> {
  let summary = "Create an i32 or i64 constant";
  // TypedAttrInterface 让 assemblyFormat 能从属性类型推导结果类型。
  let arguments = (ins TypedAttrInterface:$value);
  let results = (outs AnySignlessInteger:$result);
  let assemblyFormat = "attr-dict $value";
  let hasVerifier = 1;
}

def Toy_AddOp : Toy_Op<"add", [Pure, SameOperandsAndResultType]> {
  let summary = "Add two scalar integers of the same type, modulo 2^N";
  let arguments = (ins AnySignlessInteger:$lhs, AnySignlessInteger:$rhs);
  let results = (outs AnySignlessInteger:$result);
  // 三个类型相同，所以文本只需写一个类型。
  let assemblyFormat = "$lhs `,` $rhs attr-dict `:` type($result)";
  let hasVerifier = 1;
}

// ===== TODO(LAB2-MUL-1)：在此区域定义 toy.mul =====
// 参考上面的 Toy_AddOp，自行编写 Toy_MulOp，生成 C++ 类 mlir::toy::MulOp。
// 要求：两个 signless 整数操作数 lhs/rhs，一个结果 result；三者类型相同。
// 声明无副作用的性质，文本形式为：%product = toy.mul %a, %b : i32。
// 语义：整数乘法，结果按位宽 N 对 2^N 取模。
// 声明自定义 Verifier，在 C++ 中限制只支持 i32/i64。
// 在下面空白处完成定义；不要修改 build/ 下生成的 .inc 文件。
def Toy_MulOp : Toy_Op<"mul", [Pure, SameOperandsAndResultType]> {
  let summary = "Mul two scalar integers of the same type, modulo 2^N";
  let arguments = (ins AnySignlessInteger:$lhs, AnySignlessInteger:$rhs);
  let results = (outs AnySignlessInteger:$result);
  // 三个类型相同，所以文本只需写一个类型。
  let assemblyFormat = "$lhs `,` $rhs attr-dict `:` type($result)";
  let hasVerifier = 1;
}

// ===== TODO(LAB2-MUL-1) 结束 =====

#endif
