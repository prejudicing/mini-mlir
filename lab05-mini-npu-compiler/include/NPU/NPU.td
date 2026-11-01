#ifndef LEARNING_NPU_TD
#define LEARNING_NPU_TD
include "mlir/IR/OpBase.td"

def NPU_Dialect : Dialect {
  let name = "npu";
  let cppNamespace = "::mlir::npu";
  let summary = "A teaching NPU with explicit DRAM and tile SRAM";
}
class NPU_Op<string name> : Op<NPU_Dialect, name>;

// Buffer 写操作不声明 Pure：结果通过 C 的内存变化体现。
def NPU_MatmulOp : NPU_Op<"matmul"> {
  let summary = "Accumulate C += A * B for f32 or signed i8/i8/i32 matrices";
  let arguments = (ins AnyMemRef:$a, AnyMemRef:$b, AnyMemRef:$c);
  let assemblyFormat = "$a `,` $b `,` $c attr-dict `:` type($a) `,` type($b) `,` type($c)";
  let hasVerifier = 1;
}

def NPU_TileOp : NPU_Op<"tile"> {
  let summary = "Accumulate a bounded M/N/K tile into C";
  let arguments = (ins AnyMemRef:$a, AnyMemRef:$b, AnyMemRef:$c,
    I64Attr:$m, I64Attr:$n, I64Attr:$k,
    I64Attr:$tm, I64Attr:$tn, I64Attr:$tk);
  let assemblyFormat = [{
    $a `,` $b `,` $c `at` $m `,` $n `,` $k
    `size` $tm `,` $tn `,` $tk attr-dict
    `:` type($a) `,` type($b) `,` type($c)
  }];
  let hasVerifier = 1;
}
#endif
