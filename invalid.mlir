module {
  func.func @main() -> f32 {
    %a = arith.constant 10 : i32
    %b = arith.constant 20 : i32
    %c = arith.addi %a, %b : f32
    func.return %c : f32
  }
}
