module {
  func.func @matmul(%a: memref<5x7xf32>, %b: memref<7x6xf32>, %c: memref<5x6xf32>) {
    // 注意是累加 C += A*B；C 不一定初始为零。
    linalg.matmul ins(%a, %b : memref<5x7xf32>, memref<7x6xf32>)
                  outs(%c : memref<5x6xf32>)
    return
  }
}
