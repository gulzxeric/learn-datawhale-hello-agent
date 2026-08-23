class MemoryStore:
    """
    智能体的记忆库，负责存储用户偏好，并把记忆渲染成提示词片段。

    设计要点：
    - 只存"偏好"这类长期有效的信息，不存对话历史（对话历史由 prompt_history 负责）
    - 读写接口分开：remember()/reject() 写入，render() 读取
    - 未来若要跨会话持久化，只需在这里加 load()/save() 方法，其他文件不用动
    """

    # 连续被拒多少次后，render() 开始注入反思指令横幅
    REFLECTION_THRESHOLD = 3

    def __init__(self):
        # 每条记忆是一个字符串，例如 "预算500以内"
        self.preferences = []
        # 被拒绝的推荐，按发生顺序排列（事件流水，不去重）
        self.rejections = []

    def remember(self, content: str) -> str:
        """
        记录一条用户偏好，重复内容自动去重。

        返回值会作为 ReAct 循环中的 Observation 反馈给 Agent，
        所以要写成 Agent 能看懂的自然语言。
        """
        content = content.strip()
        if not content:
            return "错误:偏好内容为空，未记录。"

        if content in self.preferences:
            return f"该偏好之前已记录过: {content}"

        self.preferences.append(content)
        return f"已记住用户偏好: {content}"

    def reject(self, content: str) -> str:
        """
        记录一次"用户拒绝了推荐"的事件。

        与 remember() 的关键区别：
        - 偏好是事实：重复陈述只存一条（去重）
        - 拒绝是事件：每次发生都要如实计数（不去重），
          因为触发反思的依据正是"次数"
        """
        content = content.strip()
        if not content:
            return "错误:拒绝内容为空，未记录。"

        self.rejections.append(content)
        count = len(self.rejections)
        return f"已记录第{count}次被拒推荐: {content}"

    def render(self) -> str:
        """
        把当前所有记忆渲染成一段可拼接进系统提示词的文本。

        由三部分按需拼接：
        - 已知偏好（有才渲染）
        - 被拒列表（有才渲染）
        - 反思指令横幅（被拒次数达到阈值时注入，由代码精确判断，
          不依赖 LLM 自己去数记忆条目）
        """
        parts = []

        if self.preferences:
            lines = "\n".join(
                f"{i}. {pref}" for i, pref in enumerate(self.preferences, start=1)
            )
            parts.append(f"\n# 已知的用户偏好:\n{lines}")

        if self.rejections:
            lines = "\n".join(
                f"{i}. {item}" for i, item in enumerate(self.rejections, start=1)
            )
            parts.append(f"\n# 用户拒绝过的推荐:\n{lines}")

        if len(self.rejections) >= self.REFLECTION_THRESHOLD:
            n = len(self.rejections)
            banner = (
                f"\n⚠️ 反思指令: 用户已连续拒绝{n}个推荐。在继续推荐前，你必须:"
                f"\n1. 在Thought中分析这些被拒项目的共同点"
                f"\n2. 调整推荐方向重新推荐，并用remember记录新的洞察"
                f"\n3. 若实在没有头绪，改为向用户提出一个澄清问题，不要盲目再推"
            )
            parts.append(banner)

        return "".join(parts)


# 模块级单例：程序里所有地方导入的都是同一个实例，共享同一份记忆
memory_store = MemoryStore()
