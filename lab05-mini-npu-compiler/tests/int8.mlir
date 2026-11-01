// RUN: %npu-opt %s --npu-compile="quantize-int8=true a-scale=0.125 b-scale=0.25" --verify-each > %t
// RUN: %FileCheck %s --check-prefix=PLAN < %t
// RUN: %npu-translate %t | %FileCheck %s --check-prefix=ISA
// RUN: %npu-opt %s --pass-pipeline='builtin.module(convert-linalg-to-npu,npu-quantize-int8{a-scale=0.125 b-scale=0.25},npu-tile,npu-plan-memory)' --verify-each | %FileCheck %s --check-prefix=PLAN
// PLAN: func.func @quantized(
// PLAN-SAME: memref<5x7xi8> {npu.address = 0 : i64, npu.bytes = 35 : i64}
// PLAN-SAME: memref<7x6xi8> {npu.address = 64 : i64, npu.bytes = 42 : i64}
// PLAN-SAME: memref<5x6xi32> {npu.address = 128 : i64, npu.bytes = 120 : i64}
// PLAN-SAME: npu.a_scale = 1.250000e-01 : f64
// PLAN-SAME: npu.b_scale = 2.500000e-01 : f64
// PLAN-SAME: npu.c_scale = 3.125000e-02 : f64
// PLAN-SAME: npu.quantization = "symmetric-per-tensor"
// PLAN: npu.tile {{.*}} at 4, 4, 4 size 1, 2, 3
// ISA: QUANT scheme=symmetric-per-tensor a_scale=0.125 b_scale=0.25 c_scale=0.03125
// ISA: BUFFER id=0 g=0 rows=5 cols=7 dtype=i8
// ISA: BUFFER id=1 g=64 rows=7 cols=6 dtype=i8
// ISA: BUFFER id=2 g=128 rows=5 cols=6 dtype=i32
// ISA: LOAD2D g=0 s=0 rows=4 cols=4 stride=7 bytes=1
// ISA: LOAD2D g=64 s=64 rows=4 cols=4 stride=6 bytes=1
// ISA: LOAD2D g=128 s=128 rows=4 cols=4 stride=6 bytes=4
// ISA: MATMUL_I8 a=0 b=64 c=128 m=4 n=4 k=4
// ISA: STORE2D s=128 g=128 rows=4 cols=4 stride=6 bytes=4
module {
  func.func @quantized(%a: memref<5x7xf32>, %b: memref<7x6xf32>, %c: memref<5x6xf32>) {
    linalg.matmul ins(%a, %b : memref<5x7xf32>, memref<7x6xf32>) outs(%c : memref<5x6xf32>)
    return
  }
}
