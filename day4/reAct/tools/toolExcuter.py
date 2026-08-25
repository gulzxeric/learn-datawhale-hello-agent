import difflib
from typing import Dict, Any, Optional

class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> callable:
        """
        根据名称获取一个工具的执行函数。
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])

    def suggestTool(self, name: str) -> Optional[str]:
        """
        当智能体调用了不存在的工具时，模糊匹配出最相似的已注册工具名，
        用于生成纠错提示（例如 'Caculator' -> 'Calculator'）。
        """
        matches = difflib.get_close_matches(name, self.tools.keys(), n=1, cutoff=0.6)
        return matches[0] if matches else None
