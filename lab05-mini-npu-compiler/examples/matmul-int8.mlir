// Signed INT8 inputs and INT32 initial accumulator/output, already quantized on host.
module {
  func.func @matmul_int8(%a: memref<5x7xi8>, %b: memref<7x6xi8>, %c: memref<5x6xi32>) {
    linalg.matmul ins(%a, %b : memref<5x7xi8>, memref<7x6xi8>)
                  outs(%c : memref<5x6xi32>)
    return
  }
}
