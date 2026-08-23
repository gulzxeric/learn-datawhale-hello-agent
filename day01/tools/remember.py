from memory import memory_store


def remember(content: str) -> str:
    """
    把一条用户偏好写入记忆库。

    当用户表达出持久性的喜好或约束时调用本工具，例如：
    喜欢的景点类型（历史文化/自然风光）、预算范围、出行方式等。
    """
    return memory_store.remember(content)
