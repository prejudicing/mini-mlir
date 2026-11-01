// RUN: %toy-opt %s --allow-unregistered-dialect --convert-toy-to-arith --verify-diagnostics
module {
  func.func @bad() {
    // expected-error @+1 {{failed to legalize operation 'unknown.work'}}
    "unknown.work"() : () -> ()
    return
  }
}
