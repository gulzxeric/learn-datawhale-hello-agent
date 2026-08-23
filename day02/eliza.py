import re
import random

# 上下文记忆库：用于存储提取的用户关键信息
context_memory = {
    "name": None,
    "age": None,
    "occupation": None,
    "hobby": None
}

# 定义规则库:模式(正则表达式) -> 响应模板列表
rules = {
    # 上下文提取规则（姓名、年龄、职业）
    r'.*my name is ([a-zA-Z]+).*': [
        "Nice to meet you, {0}. How can I help you today?",
        "Hello {0}! I'll keep your name in mind. What would you like to discuss?"
    ],
    r'.*i am (\d+) years old.*': [
        "Got it, you are {0} years old. How do you feel about this stage of your life?",
        "Being {0} brings unique experiences. What's currently on your mind?"
    ],
    r'.*i work as a (.*)|.*i am a (.*)': [
        "Working as a {0} sounds interesting. Do you find your work fulfilling?",
        "How long have you been a {0}?"
    ],

    # 场景扩展规则（谈论工作、学习、爱好）
    r'.*my job (.*)|.*work is (.*)': [
        "Work can occupy a lot of our mental space. How is your work environment?",
        "What is the most challenging part about your job?"
    ],
    r'.*i am studying (.*)|.*i study (.*)': [
        "What motivated you to study {0}?",
        "Does studying {0} bring you more excitement or pressure?"
    ],
    r'.*i like (.*)|.*i enjoy (.*)': [
        "That sounds like a fun pastime! How long have you enjoyed {0}?",
        "What makes {0} so special to you?"
    ],
    r'I need (.*)': [
        "Why do you need {0}?",
        "Would it really help you to get {0}?",
        "Are you sure you need {0}?"
    ],
    r'Why don\'t you (.*)\?': [
        "Do you really think I don't {0}?",
        "Perhaps eventually I will {0}.",
        "Do you really want me to {0}?"
    ],
    r'Why can\'t I (.*)\?': [
        "Do you think you should be able to {0}?",
        "If you could {0}, what would you do?",
        "I don't know -- why can't you {0}?"
    ],
    r'I am (.*)': [
        "Did you come to me because you are {0}?",
        "How long have you been {0}?",
        "How do you feel about being {0}?"
    ],
    r'.* mother .*': [
        "Tell me more about your mother.",
        "What was your relationship with your mother like?",
        "How do you feel about your mother?"
    ],
    r'.* father .*': [
        "Tell me more about your father.",
        "How did your father make you feel?",
        "What has your father taught you?"
    ],
    r'.*': [
        "Please tell me more.",
        "Let's change focus a bit... Tell me about your family.",
        "Can you elaborate on that?"
    ]
}

# 定义代词转换规则
pronoun_swap = {
    "i": "you", "you": "i", "me": "you", "my": "your",
    "am": "are", "are": "am", "was": "were", "i'd": "you would",
    "i've": "you have", "i'll": "you will", "yours": "mine",
    "mine": "yours"
}

def swap_pronouns(phrase):
    """
    对输入短语中的代词进行第一/第二人称转换
    """
    words = phrase.lower().split()
    swapped_words = [pronoun_swap.get(word, word) for word in words]
    return " ".join(swapped_words)

def update_context(user_input):
    """提取并持久化用户对话中的关键实体信息"""
    name_m = re.search(r'my name is ([a-zA-Z]+)', user_input, re.IGNORECASE)
    if name_m: context_memory["name"] = name_m.group(1).capitalize()

    age_m = re.search(r'i am (\d+) years old', user_input, re.IGNORECASE)
    if age_m: context_memory["age"] = age_m.group(1)

    job_m = re.search(r'(?:work as a|i am a) ([a-zA-Z\s]+)', user_input, re.IGNORECASE)
    if job_m and not job_m.group(1).strip().isdigit():
        context_memory["occupation"] = job_m.group(1).strip()

    hobby_m = re.search(r'i (?:like|enjoy) (.*)', user_input, re.IGNORECASE)
    if hobby_m: context_memory["hobby"] = hobby_m.group(1).strip()

def respond(user_input):
    update_context(user_input)
    
    for pattern, responses in rules.items():
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            # 搜寻非空的捕获组
            captured_group = ""
            if match.groups():
                for g in match.groups():
                    if g:
                        captured_group = g
                        break
            
            swapped_group = swap_pronouns(captured_group)
            response = random.choice(responses)
            if "{0}" in response:
                response = response.format(swapped_group)
            
            # 概率性（30%）主动唤起上下文记忆，增加人性化关联
            if random.random() < 0.30 and pattern != r'.*':
                if context_memory["name"] and "Nice to meet you" not in response:
                    response = f"{context_memory['name']}, " + response[0].lower() + response[1:]
                elif context_memory["occupation"]:
                    response += f" (Does this relate to your work as a {context_memory['occupation']}?)"
            return response

    # 兜底情况：若触发通配符且拥有记忆，优先引用记忆
    if any(context_memory.values()):
        memories = [f"{k}: {v}" for k, v in context_memory.items() if v]
        return f"Earlier you mentioned {random.choice(memories)}. How does that connect to what you're saying now?"

    return random.choice(rules[r'.*'])

# 主聊天循环
if __name__ == '__main__':
    print("Therapist: Hello! How can I help you today?")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Therapist: Goodbye. It was nice talking to you.")
            break
        response = respond(user_input)
        print(f"Therapist: {response}")
        