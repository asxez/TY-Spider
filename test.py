def not_question() -> dict[str, str | int]:
    return {
        'status': 2,
        'response': '未输入内容'
    }

print(not_question())