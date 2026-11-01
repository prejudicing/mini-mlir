module {
  // 非常量 x：验证连续重写不依赖常量折叠。
  // CHECK-LABEL: func.func @chain(
  // CHECK-SAME: %[[X:.*]]: i32)
  // CHECK-NOT: arith.addi
  // CHECK: return %[[X]] : i32
  func.func @chain(%x: i32) -> i32 {
    %zero = arith.constant 0 : i32
    %a = arith.addi %x, %zero : i32
    %b = arith.addi %a, %zero : i32
    %c = arith.addi %b, %zero : i32
    return %c : i32
  }

  // 右操作数为非零常量，必须保留。
  // CHECK-LABEL: func.func @nonzero(
  // CHECK: arith.addi
  // CHECK: return
  func.func @nonzero(%x: i32) -> i32 {
    %one = arith.constant 1 : i32
    %sum = arith.addi %x, %one : i32
    return %sum : i32
  }

  // 本实验仅实现 x + 0，尚未扩展到 0 + x。
  // CHECK-LABEL: func.func @zero_on_left(
  // CHECK: arith.addi
  // CHECK: return
  func.func @zero_on_left(%x: i32) -> i32 {
    %zero = arith.constant 0 : i32
    %sum = arith.addi %zero, %x : i32
    return %sum : i32
  }

  // SSA 名称叫 zero 并不意味着它的运行时值是零。
  // CHECK-LABEL: func.func @unknown_rhs(
  // CHECK: arith.addi
  // CHECK: return
  func.func @unknown_rhs(%x: i32, %zero: i32) -> i32 {
    %sum = arith.addi %x, %zero : i32
    return %sum : i32
  }
}
