// RUN: %npu-opt %s --convert-linalg-to-npu --verify-each | %FileCheck %s --check-prefix=LOWER
// RUN: %npu-opt %s --npu-compile --verify-each > %t
// RUN: %FileCheck %s --check-prefix=PLAN < %t
// RUN: %npu-translate %t | %FileCheck %s --check-prefix=ISA
// LOWER: npu.matmul
// LOWER-NOT: linalg.matmul
// PLAN: npu.address = 0 : i64
// PLAN-SAME: npu.bytes = 140 : i64
// PLAN-SAME: npu.address = 192 : i64
// PLAN-SAME: npu.address = 384 : i64
// PLAN-SAME: npu.sram_bytes = 192 : i64
// PLAN: npu.tile {{.*}} at 0, 0, 0 size 4, 4, 4
// PLAN: npu.tile {{.*}} at 0, 0, 4 size 4, 4, 3
// PLAN: npu.tile {{.*}} at 4, 4, 4 size 1, 2, 3
// PLAN-NOT: npu.matmul
// ISA: FUNC matmul sram=192
// ISA: BUFFER id=0 g=0 rows=5 cols=7
// ISA: BUFFER id=1 g=192 rows=7 cols=6
// ISA: BUFFER id=2 g=384 rows=5 cols=6
// ISA: LOAD2D g=0 s=0 rows=4 cols=4 stride=7
// ISA: LOAD2D g=192 s=64 rows=4 cols=4 stride=6
// ISA: LOAD2D g=384 s=128 rows=4 cols=4 stride=6
// ISA: MATMUL a=0 b=64 c=128 m=4 n=4 k=4
// ISA: STORE2D s=128 g=384 rows=4 cols=4 stride=6
// ISA: END
module {
  func.func @matmul(%a: memref<5x7xf32>, %b: memref<7x6xf32>, %c: memref<5x6xf32>) {
    linalg.matmul ins(%a, %b : memref<5x7xf32>, memref<7x6xf32>) outs(%c : memref<5x6xf32>)
    return
  }
}
