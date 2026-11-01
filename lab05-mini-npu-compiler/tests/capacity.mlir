// RUN: %npu-opt %s --npu-compile="sram-bytes=128" --verify-diagnostics
module {
  func.func @capacity(%a: memref<4x4xf32>, %b: memref<4x4xf32>, %c: memref<4x4xf32>) {
    // expected-error @+1 {{tile exceeds SRAM capacity: requires 192 bytes, available 128}}
    linalg.matmul ins(%a, %b : memref<4x4xf32>, memref<4x4xf32>) outs(%c : memref<4x4xf32>)
    return
  }
}
