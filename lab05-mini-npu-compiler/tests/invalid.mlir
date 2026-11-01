// RUN: %npu-opt %s --split-input-file --verify-diagnostics
module {
  func.func @shape(%a: memref<2x3xf32>, %b: memref<4x2xf32>, %c: memref<2x2xf32>) {
    // expected-error @+1 {{requires A[M,K], B[K,N], C[M,N]}}
    npu.matmul %a, %b, %c : memref<2x3xf32>, memref<4x2xf32>, memref<2x2xf32>
    return
  }
}
// -----
module {
  func.func @dynamic(%a: memref<?x3xf32>, %b: memref<3x2xf32>, %c: memref<2x2xf32>) {
    // expected-error @+1 {{requires static rank-2 row-major memrefs}}
    npu.matmul %a, %b, %c : memref<?x3xf32>, memref<3x2xf32>, memref<2x2xf32>
    return
  }
}
// -----
module {
  func.func @bounds(%a: memref<2x3xf32>, %b: memref<3x2xf32>, %c: memref<2x2xf32>) {
    // expected-error @+1 {{tile offsets/sizes are out of matrix bounds}}
    npu.tile %a, %b, %c at 1, 0, 0 size 2, 2, 3 : memref<2x3xf32>, memref<3x2xf32>, memref<2x2xf32>
    return
  }
}
// -----
module {
  func.func @alias(%a: memref<2x2xf32>, %b: memref<2x2xf32>) {
    // expected-error @+1 {{output must not alias an input SSA buffer}}
    npu.matmul %a, %b, %a : memref<2x2xf32>, memref<2x2xf32>, memref<2x2xf32>
    return
  }
}
