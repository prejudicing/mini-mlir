// CHECK-LABEL: func.func @main()
// CHECK: %[[TEN:.*]] = arith.constant 10 : i32
// CHECK-NOT: arith.addi
// CHECK: return %[[TEN]] : i32
// CHECK-LABEL: func.func @test_no_opt()
// CHECK: %[[A:.*]] = arith.constant 10 : i32
// CHECK: %[[B:.*]] = arith.constant 20 : i32
// CHECK: %[[SUM:.*]] = arith.addi %[[A]], %[[B]] : i32
// CHECK: return %[[SUM]] : i32

module {
  func.func @main() -> i32 {
    %a = arith.constant 10 : i32
    %zero = arith.constant 0 : i32

    %b = arith.addi %a, %zero : i32
    %c = arith.addi %b, %zero : i32

    func.return %c : i32
  }

  func.func @test_no_opt() -> i32 {
    %a = arith.constant 10 : i32
    %b = arith.constant 20 : i32

    %c = arith.addi %a, %b : i32

    func.return %c : i32
  }
}
