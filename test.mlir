module {
  func.func @main() -> i32 {
    %a = arith.constant 10 : i32
    %b = arith.constant 20 : i32
    %c = arith.addi %a, %b : i32
    func.return %c : i32
  }
}