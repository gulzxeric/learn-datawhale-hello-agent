# 统一的工具注册表：Agent 能用什么工具，就看这个字典
from tools.get_attraction import get_attraction
from tools.get_weather import get_weather
from tools.remember import remember
from tools.reject import reject

available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
    "remember": remember,
    "reject": reject,
}