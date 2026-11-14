// CHECK-LABEL: func.func @add64(
// CHECK: toy.add
// CHECK: return
// CHECK-LABEL: func.func @negative()
// CHECK: toy.constant -10 : i64
// CHECK: return
// CHECK-LABEL: func.func @generic()
// CHECK: toy.constant 7 : i32
// CHECK: return
// CHECK-LABEL: func.func @mul32(
// CHECK: toy.mul
// CHECK: return
// CHECK-LABEL: func.func @mul64(
// CHECK: toy.mul
// CHECK: return
module {
  func.func @add64(%a: i64, %b: i64) -> i64 {
    %sum = toy.add %a, %b : i64
    return %sum : i64
  }
  func.func @negative() -> i64 {
    %c = toy.constant -10 : i64
    return %c : i64
  }
  func.func @generic() -> i32 {
    %c = "toy.constant"() {value = 7 : i32} : () -> i32
    return %c : i32
  }

  // ===== TODO(LAB2-MUL-4)：在此区域增加合法乘法函数 =====
  // 编写 mul32 和 mul64，分别接收两个 i32 / i64 参数，返回 toy.mul 的结果。
  // 在文件顶部增加对应的 FileCheck 标签和输出检查，确认输出中确实有 toy.mul。
  // 原有测试脚本会自动测试本文件的简写/通用语法往返，不需要新增测试入口。
  func.func @mul32(%a :i32,%b : i32) -> i32 {
    %c = toy.mul %a, %b : i32
    return %c : i32
}
  func.func @mul64(%a :i64,%b : i64) -> i64 {
    %c = toy.mul %a, %b : i64
    return %c : i64
}

  // ===== TODO(LAB2-MUL-4) 结束 =====
}
