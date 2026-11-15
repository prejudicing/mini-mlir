#include <charconv>
#include <cstdint>
#include <iostream>
#include <string_view>

// 限制输入范围，确保加、减、乘的结果都能放进 int64_t。
bool parseInteger(std::string_view text, int64_t &value) {
  auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
  return error == std::errc{} && end == text.data() + text.size() &&
         value >= -1000000000 && value <= 1000000000;
}

int main(int argc, char **argv) {
  if (argc != 4) {
    std::cerr << "Usage: calculator <add|sub|mul|div> <lhs> <rhs>\n";
    return 2;
  }
  int64_t lhs = 0, rhs = 0;
  if (!parseInteger(argv[2], lhs) || !parseInteger(argv[3], rhs)) {
    std::cerr << "error: operands must be integers in [-1000000000, 1000000000]\n";
    return 2;
  }
  std::string_view operation = argv[1];
  int64_t result = 0;
  if (operation == "add") result = lhs + rhs;
  else if (operation == "sub") result = lhs - rhs;
  else if (operation == "mul") result = lhs * rhs;
  else if (operation == "div") {
    if (rhs == 0) {
      std::cerr << "error: division by zero\n";
      return 2;
    }
    result = lhs / rhs; // 整数除法，向零截断，例如 -7 / 2 == -3。
  } else {
    std::cerr << "error: unknown operation '" << operation << "'\n";
    return 2;
  }
  std::cout << "result: " << result << '\n';
  return 0;
}
