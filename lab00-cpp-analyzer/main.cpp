#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"

#include "mlir/IR/BuiltinOps.h"
#include "mlir/IR/DialectRegistry.h"
#include "mlir/IR/MLIRContext.h"

#include "mlir/Parser/Parser.h"

#include "mlir/Pass/Pass.h"
#include "mlir/Pass/PassManager.h"

#include "llvm/Support/raw_ostream.h"

#include <memory>

using namespace mlir;

// 1. 定义自己的 Pass
struct AddIOpAnalysisPass
    : public PassWrapper<
          AddIOpAnalysisPass,
          OperationPass<ModuleOp>> {

    // 2. Pass 的执行入口
    void runOnOperation() override {

        // 获取当前处理的 Module
        ModuleOp module = getOperation();

        int addCount = 0;

        // 遍历 Module 内部的 Operation
        module.walk([&](arith::AddIOp op) {

            addCount++;

            llvm::outs() << "\nFound arith.addi #"
                         << addCount << "\n";

            Value lhs = op.getLhs();
            Value rhs = op.getRhs();
            Value result = op.getResult();

            llvm::outs() << "Operand count: "
                         << op->getNumOperands() << "\n";

            llvm::outs() << "Result count: "
                         << op->getNumResults() << "\n";

            llvm::outs() << "LHS type: "
                         << lhs.getType() << "\n";

            llvm::outs() << "RHS type: "
                         << rhs.getType() << "\n";

            llvm::outs() << "Result type: "
                         << result.getType() << "\n";
        });

        llvm::outs() << "\nTotal arith.addi: "
                     << addCount << "\n";
    }
};

int main(int argc, char **argv) {

    if (argc != 2) {
        llvm::errs() << "Usage: "
                     << argv[0]
                     << " <input.mlir>\n";
        return 1;
    }

    // 注册 Dialect
    DialectRegistry registry;

    registry.insert<
        arith::ArithDialect,
        func::FuncDialect
    >();

    // 创建上下文
    MLIRContext context(registry);

    // 解析 MLIR
    auto module = parseSourceFile<ModuleOp>(
        argv[1],
        &context
    );

    if (!module) {
        llvm::errs() << "Parse failed\n";
        return 1;
    }

    // 3. 创建 Pass Manager
    PassManager pm(&context);

    // 4. 添加自定义 Pass
    pm.addPass(
        std::make_unique<AddIOpAnalysisPass>()
    );

    // 5. 执行 Pass Pipeline
    if (failed(pm.run(*module))) {
        llvm::errs() << "Pass execution failed\n";
        return 1;
    }

    return 0;
}