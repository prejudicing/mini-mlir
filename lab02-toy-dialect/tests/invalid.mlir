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

// ===== TODO(LAB2-MUL-5)：在此区域增加非法乘法用例 =====
// 每个新片段前使用本文件已有的分隔注释（五个短横线），以便独立解析。
// 至少覆盖：
// 1. 两个 i16 输入和 i16 结果：由手写 Verifier 拒绝。
// 2. i32 与 i64 混用：用通用语法显式写出类型，由类型一致性约束拒绝。
// 3. 两个 f32 输入和 f32 结果：由整数类型约束拒绝。
// 参考上方各用例，为实际出错行添加预期诊断注释，并运行诊断测试。
// 不要把“未知操作 toy.mul”的错误当作上述测试通过的依据。

// -----
module {
  func.func @i16_mul(%a: i16, %b: i16) -> i16 {
    // expected-error @+1 {{only supports scalar i32 or i64, got 'i16'}}
    %c = "toy.mul"(%a, %b) : (i16,i16) -> i16
    return %c : i16
  }
}

// -----
module {
  func.func @i3264_mul(%a: i32, %b: i64) -> i32 {
    // expected-error @+1 {{requires the same type for all operands and results}}
    %c = "toy.mul"(%a, %b) : (i32,i64) -> i32
    return %c : i32
  }
}
// -----

module {
  func.func @float_mul(%a: f32, %b: f32) -> f32 {
    // expected-error @+1 {{must be signless integer}}
    %c = "toy.mul"(%a, %b) : (f32, f32) -> f32
    return %c : f32
  }
}


// ===== TODO(LAB2-MUL-5) 结束 =====
