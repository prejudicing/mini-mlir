// CHECK-LABEL: func.func @add64(
// CHECK: toy.add
// CHECK: return
// CHECK-LABEL: func.func @negative()
// CHECK: toy.constant -10 : i64
// CHECK: return
// CHECK-LABEL: func.func @generic()
// CHECK: toy.constant 7 : i32
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
}
