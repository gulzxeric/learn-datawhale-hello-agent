from memory import memory_store


def reject(content: str) -> str:
    """
    记录一次"用户拒绝了当前推荐"的事件。

    当用户明确表示对推荐不满意时调用本工具，例如：
    "不感兴趣"、"不喜欢这个"、"换个别的"。
    被拒次数会被精确统计，用于触发推荐策略反思。
    """
    return memory_store.reject(content)
