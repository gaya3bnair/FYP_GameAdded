from condition.adhdCondition import generate_questions as adhd_q, calculate_severity as adhd_s
from condition.anxiety import generate_questions as anx_q, calculate_severity as anx_s
from condition.ocdCondition import generate_questions as ocd_q, calculate_severity as ocd_s

# Active sessions (temporary in-memory)
user_sessions = {}

def start_condition_test(user, condition):
    if condition == "adhd":
        questions = adhd_q()
    elif condition == "anxiety":
        questions = anx_q()
    elif condition == "ocd":
        questions = ocd_q()
    else:
        return None

    user_sessions[user] = {
        "condition": condition,
        "questions": questions,
        "index": 0,
        "score": 0
    }

    return questions[0]


def process_answer(user, answer):
    session = user_sessions.get(user)
    if not session:
        return None

    try:
        score = int(answer)
        if score < 0 or score > 4:
            return "Please enter a number between 0 and 4."
    except:
        return "Invalid input. Enter 0-4."

    session["score"] += score
    session["index"] += 1

    # Next question
    if session["index"] < len(session["questions"]):
        return session["questions"][session["index"]]

    # Finish test
    total = session["score"]
    condition = session["condition"]

    if condition == "adhd":
        result = adhd_s(total)
    elif condition == "anxiety":
        result = anx_s(total)
    elif condition == "ocd":
        result = ocd_s(total)

    del user_sessions[user]

    return f"✅ Test Completed!\nTotal Score: {total}\nResult: {result}"