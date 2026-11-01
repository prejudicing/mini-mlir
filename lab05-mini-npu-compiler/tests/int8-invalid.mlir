// RUN: %npu-opt %s --verify-diagnostics
module {
  func.func @bad_accumulator(%a: memref<2x2xi8>, %b: memref<2x2xi8>, %c: memref<2x2xi8>) {
    // expected-error @+1 {{requires element types f32/f32/f32 or signed i8/i8/i32}}
    npu.matmul %a, %b, %c : memref<2x2xi8>, memref<2x2xi8>, memref<2x2xi8>
    return
  }
}
