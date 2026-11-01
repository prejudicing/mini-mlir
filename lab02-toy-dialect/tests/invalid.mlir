// -split-input-file 让每个分隔片段独立解析、验证。
module {
  func.func @bad_constant() -> i16 {
    // expected-error @+1 {{only supports scalar i32 or i64, got 'i16'}}
    %c = toy.constant 1 : i16
    return %c : i16
  }
}

// -----

module {
  func.func @bad_add(%a: i8, %b: i8) -> i8 {
    // expected-error @+1 {{only supports scalar i32 or i64, got 'i8'}}
    %c = toy.add %a, %b : i8
    return %c : i8
  }
}

// -----

module {
  func.func @mismatched_add(%a: i32, %b: i64) -> i32 {
    // 通用语法绕过简写语法的类型推导，直接测试 ODS 的类型一致性检查。
    // expected-error @+1 {{requires the same type for all operands and results}}
    %c = "toy.add"(%a, %b) : (i32, i64) -> i32
    return %c : i32
  }
}

// -----

module {
  func.func @mismatched_constant() -> i64 {
    // expected-error @+1 {{failed to verify that all of {value, result} have same type}}
    %c = "toy.constant"() {value = 1 : i32} : () -> i64
    return %c : i64
  }
}

// -----

module {
  func.func @float_add(%a: f32, %b: f32) -> f32 {
    // expected-error @+1 {{must be signless integer}}
    %c = "toy.add"(%a, %b) : (f32, f32) -> f32
    return %c : f32
  }
}
