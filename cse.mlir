module {
  func.func @main() -> i32 {
    %a = arith.constant 10 : i32
    %b = arith.constant 20 : i32

    %c = arith.addi %a, %b : i32
    %d = arith.addi %a, %b : i32

    %e = arith.addi %c, %d : i32
    func.return %e : i32
  }
}
