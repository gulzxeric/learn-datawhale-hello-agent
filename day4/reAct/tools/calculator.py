import ast
import operator

# 二元运算符白名单
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# 一元运算符白名单
_UNARY_OPS = {
    ast.UAdd: lambda x: +x,
    ast.USub: lambda x: -x,
}

# 常见的中文/全角数学符号到 ASCII 运算符的映射
_SYMBOL_MAP = {
    "×": "*",
    "÷": "/",
    "＋": "+",
    "－": "-",
    "−": "-",
    "（": "(",
    "）": ")",
    "，": ",",
    "^": "**",
}


def _normalize(expression: str) -> str:
    """将中文/全角数学符号归一化为 ASCII 运算符，并去掉末尾的等号和问号。"""
    for src, dst in _SYMBOL_MAP.items():
        expression = expression.replace(src, dst)
    return expression.strip().strip("=？? ").strip()


def _eval_node(node):
    """递归求值 AST 节点，仅允许白名单中的安全运算。"""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"表达式中包含不支持的内容: {type(node).__name__}")


def calculate(expression: str) -> str:
    """
    一个安全的数学计算器工具。
    它将表达式解析为 AST 并只执行白名单内的算术运算，
    因此不会执行任意代码，可以放心接收 LLM 生成的输入。
    """
    print(f"🧮 正在计算表达式: {expression}")
    try:
        normalized = _normalize(expression)
        tree = ast.parse(normalized, mode="eval")
        result = _eval_node(tree)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"'{expression}' 的计算结果是: {result}"
    except ZeroDivisionError:
        return "计算出错:除数不能为零。"
    except Exception as e:
        return f"计算出错:{e}"
