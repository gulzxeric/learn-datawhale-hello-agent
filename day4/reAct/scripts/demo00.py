import os
import re
import sys

# 将 day4 目录加入 Python 搜索路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)

from day4.reAct.llm import HelloAgentsLLM
from day4.reAct.tools.toolExcuter import ToolExecutor
from day4.reAct.tools.search import search
from day4.reAct.tools.calculator import calculate

# ReAct 提示词模板
REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`:调用一个可用工具。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 Finish[最终答案] 来输出最终答案。

现在，请开始解决以下问题:
Question: {question}
History: {history}
{warning}
"""


# 工具观察结果中表示"调用失败"的前缀（与 tools/ 下各工具返回的错误格式对应）
_ERROR_PREFIXES = ("错误:", "计算出错:", "搜索时发生错误:")


class ReActAgent:
    def __init__(
        self,
        llm_client: HelloAgentsLLM,
        tool_executor: ToolExecutor,
        max_steps: int = 5,
        max_failures: int = 4,
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.max_failures = max_failures
        self.history = []

    def run(self, question: str):
        """
        运行ReAct智能体来回答一个问题。
        """
        self.history = []  # 每次运行时重置历史记录
        current_step = 0
        consecutive_failures = 0

        def record_failure(observation: str):
            """记录一次失败并写回历史。达到连续失败上限时返回终止消息，否则返回 None。"""
            nonlocal consecutive_failures
            consecutive_failures += 1
            print(f"⚠️ 连续失败次数: {consecutive_failures}/{self.max_failures}")
            self.history.append(f"Observation: {observation}")
            if consecutive_failures >= self.max_failures:
                msg = f"任务失败:已连续 {consecutive_failures} 次工具调用失败，为避免无效循环已强制终止。"
                print(f"⛔ {msg}")
                return msg
            return None

        while current_step < self.max_steps:
            current_step += 1
            print(f"--- 第 {current_step} 步 ---")

            # 1. 格式化提示词（连续失败达到阈值时注入纠错警告块）
            tools_desc = self.tool_executor.getAvailableTools()
            print(tools_desc)
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc, question=question, history=history_str,
                warning=self._buildWarning(consecutive_failures),
            )

            # 2. 调用LLM进行思考
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)

            if not response_text:
                print("错误:LLM未能返回有效响应。")
                break

            # 3. 解析LLM的输出
            thought, action = self._parse_output(response_text)

            if thought:
                print(f"思考: {thought}")

            if not action:
                # 兜底:模型有时会省略 Action: 前缀而直接输出 Finish[最终答案]
                finish_match = re.search(r"Finish\[(.*)\]", response_text)
                if finish_match:
                    final_answer = finish_match.group(1)
                    print(f"🎉 最终答案: {final_answer}")
                    return final_answer
                # 不再静默终止，而是把解析错误作为观察结果反馈给模型，引导其自行纠正
                observation = (
                    "错误:无法从你的回复中解析出有效的Action。\n"
                    f"可用工具:\n{tools_desc}\n"
                    "正确格式示例: Action: Calculator[(123+456)*789/12] 或 Finish[最终答案]"
                )
                abort = record_failure(observation)
                if abort:
                    return abort
                continue

            # 4. 执行Action
            if action.startswith("Finish"):
                # 如果是Finish指令，提取最终答案并结束
                final_answer = re.match(r"Finish\[(.*)\]", action).group(1)
                print(f"🎉 最终答案: {final_answer}")
                return final_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                # Action 格式非法:反馈正确格式，计入一次失败
                observation = (
                    f"错误:无法解析Action '{action}'。\n"
                    "正确格式: Action: 工具名[参数]，例如 Calculator[(123+456)*789/12]，"
                    "结束回答请使用 Finish[最终答案]。"
                )
                self.history.append(f"Action: {action}")
                abort = record_failure(observation)
                if abort:
                    return abort
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                # 工具名不存在:附上可用工具清单和相似工具名建议，帮助模型纠正
                suggestion = self.tool_executor.suggestTool(tool_name)
                suggestion_hint = f"你是否想使用 '{suggestion}'?" if suggestion else ""
                observation = (
                    f"错误:未找到名为 '{tool_name}' 的工具。{suggestion_hint}\n"
                    f"可用工具:\n{tools_desc}\n"
                    "正确调用格式: Action: 工具名[参数]"
                )
            else:
                observation = tool_function(tool_input)  # 调用真实工具

            print(f"👀 观察: {observation}")

            # 失败感知:错误观察计入连续失败并升级纠错力度；成功调用则清零计数
            if self._isFailedObservation(observation):
                self.history.append(f"Action: {action}")
                abort = record_failure(observation)
                if abort:
                    return abort
                continue

            consecutive_failures = 0

            # 将本轮的Action和Observation添加到历史记录中
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        print("已达到最大步数，流程终止。")
        return None

    # (这些方法是 ReActAgent 类的一部分)
    def _buildWarning(self, failures: int) -> str:
        """连续失败达到阈值时，生成注入到提示词中的纠错警告块。"""
        if failures < 2:
            return ""
        return (
            f"\n【重要警告】你已经连续 {failures} 次调用工具失败!\n"
            "请务必:\n"
            "1. 逐字核对上方工具清单中的工具名称，拼写必须完全一致;\n"
            "2. 检查参数是否符合工具描述中给出的格式与示例;\n"
            "3. 禁止重复与之前完全相同的错误调用，必要时换用其他工具。\n"
        )

    def _isFailedObservation(self, observation: str) -> bool:
        """根据观察结果前缀判断本次工具调用是否失败。"""
        return isinstance(observation, str) and observation.startswith(_ERROR_PREFIXES)

    def _parse_output(self, text: str):
        """解析LLM的输出，提取Thought和Action。"""
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 只匹配当前行，避免把后续的 Finish/Observation 行一并当作工具输入
        action_match = re.search(r"Action:[ \t]*(.*)", text)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        """解析Action字符串，提取工具名称和输入。"""
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None
    
if __name__ == '__main__':
    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)
    calculator_desc = "一个精确的数学计算器。当需要进行加减乘除、幂运算等复杂数值计算时应使用此工具，输入为合法的数学表达式，例如 (123+456)*789/12。"
    tool_executor.registerTool("Calculator", calculator_desc, calculate)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "计算 (123 + 456) × 789 / 12 = ? 的结果"
    agent.run(question)