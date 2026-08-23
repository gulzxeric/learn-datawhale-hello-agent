import os
import re
from dotenv import load_dotenv
from tools.tools import available_tools
from llm import OpenAICompatibleClient
from memory import memory_store

load_dotenv()


AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市和天气搜索推荐的旅游景点。
- `remember(content: str)`: 把一条用户偏好写入长期记忆。
- `reject(content: str)`: 记录一次"用户拒绝了当前推荐"的事件。

# 记忆使用规则:
- 当用户表达出持久性的偏好或约束时（如"我喜欢历史文化景点"、"预算500以内"），必须先调用 remember 工具记录，再继续处理用户的请求。
- 提示词末尾的"已知的用户偏好"部分是你的长期记忆。做推荐时应主动遵守这些偏好，无需用户重复说明。

# 售罄应对规则:
- 当用户告知某景点门票已售罄或无法预约时，必须按以下步骤处理：
  1. 先调用 remember 工具记录"XX门票售罄"，避免后续重复推荐该景点
  2. 重新调用 get_attraction 搜索同城市备选景点，并在 Thought 中明确排除已售罄的景点
  3. 推荐备选方案时，简要说明替换原因
- 禁止仅回复道歉或遗憾就结束任务，必须给出可执行的备选方案。

# 连续拒绝应对规则:
- 当用户表示对推荐不满意时（如"不感兴趣"、"不喜欢"、"换个"），必须先调用 reject 工具记录这次拒绝，再继续处理用户的请求。
- 如果提示词中出现"⚠️ 反思指令"横幅，说明用户已连续多次拒绝，你必须：
  1. 在 Thought 中认真分析所有被拒项目的共同点（类型、氛围、价格等），并对照已知的用户偏好找出偏差
  2. 若能推断出新的方向：调整推荐角度重新搜索，并用 remember 记录新洞察（如"用户可能更喜欢自然风光而非历史古迹"）
  3. 若实在推断不出方向：用 Finish 向用户提出一个具体的澄清问题，不要盲目再推
- 任何时候推荐景点，都必须避开"用户拒绝过的推荐"列表中已有的项目。

# 输出格式要求:
你的每次回复必须严格遵循以下格式，包含一对Thought和Action：

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一：
1. 调用工具：function_name(arg_name="arg_value")
2. 结束任务：Finish[最终答案]

# 重要提示:
- 每次只输出一对Thought-Action
- Action必须在同一行，不要换行
- 调用工具时必须提供工具签名中列出的全部必填参数，不要自行省略
- 当收集到足够信息可以回答用户问题时，必须使用 Action: Finish[最终答案] 格式结束

请开始吧！
"""


# --- 1. 配置LLM客户端 ---
# 请根据您使用的服务，将这里替换成对应的凭证和地址

API_KEY = os.environ.get("AGNES_API_KEY")
BASE_URL = "https://apihub.agnes-ai.com/v1"
MODEL_ID = "agnes-2.5-flash"
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
# os.environ["TAVILY_API_KEY"] = "YOUR_TAVILY_API_KEY"

llm = OpenAICompatibleClient(model=MODEL_ID, api_key=API_KEY, base_url=BASE_URL)

# --- 2. 单次任务的ReAct循环 ---
def run_react_task(user_prompt: str):
    """针对一条用户输入，运行一轮完整的 Thought→Action→Observation 循环。"""
    print(f"用户输入: {user_prompt}\n" + "=" * 40)
    prompt_history = [f"用户请求: {user_prompt}"]

    for i in range(5):  # 设置最大循环次数
        print(f"--- 循环 {i+1} ---\n")

        # 2.1. 构建Prompt（系统提示词每次都重新拼接，确保最新记忆被注入）
        full_prompt = "\n".join(prompt_history)
        system_prompt = AGENT_SYSTEM_PROMPT + memory_store.render()

        # 2.2. 调用LLM进行思考
        llm_output = llm.generate(full_prompt, system_prompt=system_prompt)
        # 模型可能会输出多余的Thought-Action，需要截断
        match = re.search(
            r"(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)",
            llm_output,
            re.DOTALL,
        )
        if match:
            truncated = match.group(1).strip()
            if truncated != llm_output.strip():
                llm_output = truncated
                print("已截断多余的 Thought-Action 对")
        print(f"模型输出:\n{llm_output}\n")
        prompt_history.append(llm_output)

        # 2.3. 解析并执行行动
        action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "=" * 40)
            prompt_history.append(observation_str)
            continue
        action_str = action_match.group(1).strip()

        if action_str.startswith("Finish"):
            finish_match = re.match(r"Finish\[(.*)\]", action_str)
            if not finish_match:
                observation = "错误: Finish 格式不正确。请使用 Finish[最终答案] 格式。"
                prompt_history.append(f"Observation: {observation}")
                continue
            final_answer = finish_match.group(1)
            print(f"任务完成，最终答案: {final_answer}")
            return final_answer

        tool_name_match = re.search(r"(\w+)\(", action_str)
        args_match = re.search(r"\((.*)\)", action_str, re.DOTALL)
        if not tool_name_match or not args_match:
            observation = "错误: 无法解析工具调用。正确格式如 get_weather(city=\"北京\")"
            prompt_history.append(f"Observation: {observation}")
            continue
        tool_name = tool_name_match.group(1)
        kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_match.group(1)))

        if tool_name in available_tools:
            try:
                observation = available_tools[tool_name](**kwargs)
            except TypeError as e:
                # LLM给出的参数可能缺失或多余（它是不可信输入）。
                # 把异常转成 Observation 反馈给Agent，让它自行修正后重试，
                # 而不是让整个程序崩溃。
                observation = f"错误: 调用工具 '{tool_name}' 时参数不正确 - {e}。请严格按照工具签名提供全部必填参数后重试。"
        else:
            observation = f"错误:未定义的工具 '{tool_name}'"

        # 2.4. 记录观察结果
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)

    print("已达最大循环次数，任务未能完成。")


# --- 3. 交互式主循环 ---
def main():
    """命令行交互入口：每条用户输入触发一次独立的 ReAct 任务，记忆全程共享。"""
    print("智能旅行助手已启动（输入 '退出' 结束对话）")
    print("试试先告诉我你的偏好，比如：我喜欢历史文化景点，预算500以内")

    while True:
        try:
            user_input = input("\n你> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("退出", "exit", "q", "quit"):
            print("再见！")
            break

        run_react_task(user_input)


if __name__ == "__main__":
    main()
