#ifndef LAB03_TOY_CONVERSION_H
#define LAB03_TOY_CONVERSION_H
#include <memory>
namespace mlir {
class Pass;
namespace toy {
std::unique_ptr<Pass> createConvertToyToArithPass();
void registerToyConversionPasses();
} // namespace toy
} // namespace mlir
#endif
