#ifndef TOY_DIALECT_TD
#define TOY_DIALECT_TD

include "mlir/IR/OpBase.td"

def Toy_Dialect : Dialect {
  let name = "toy";
  let cppNamespace = "::mlir::toy";
  let summary = "A small scalar integer dialect for learning MLIR";
  let description = [{
    This lab dialect supports scalar i32 and i64 constants and addition.
    Addition wraps modulo 2^N, matching arith.addi without overflow flags.
    It is an independent teaching dialect, not the upstream tensor Toy tutorial.
  }];
}

#endif
