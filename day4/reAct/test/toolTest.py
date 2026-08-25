import os
import sys

# 将 day4 目录加入 Python 搜索路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)

from day4.reAct.tools.search import search
from day4.reAct.tools.calculator import calculate
from day4.reAct.tools.toolExcuter import ToolExecutor

# --- 工具初始化与使用示例 ---
if __name__ == '__main__':
    # 1. 初始化工具执行器
    toolExecutor = ToolExecutor()

    # 2. 注册我们的实战搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)

    # 3. 注册计算器工具
    calculator_description = "一个精确的数学计算器。当需要进行加减乘除、幂运算等复杂数值计算时应使用此工具，输入为合法的数学表达式，例如 (123+456)*789/12。"
    toolExecutor.registerTool("Calculator", calculator_description, calculate)

    # 4. 打印可用的工具
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 5. 测试计算器工具的各种用例
    print("\n--- 执行 Calculator 工具测试用例 ---")
    calculator_test_cases = [
        "(123 + 456) × 789 / 12",  # 任务中的原始问题，含中文乘号
        "(123+456)÷3 + 2**8",      # 中文除号 + 幂运算
        "-5 * (3 + 2)",            # 负数与括号
        "10 / 0",                  # 除零错误
        "__import__('os').getcwd()",  # 非法输入，应被拒绝
        "1 +",                     # 语法错误
    ]
    calculator_function = toolExecutor.getTool("Calculator")
    for case in calculator_test_cases:
        observation = calculator_function(case)
        print(f"输入: {case}\n观察: {observation}\n")

    # 6. 智能体的Action调用，这次我们问一个实时性的问题
    print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    tool_name = "Search"
    tool_input = "英伟达最新的GPU型号是什么"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误:未找到名为 '{tool_name}' 的工具。")
        