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

#endif
