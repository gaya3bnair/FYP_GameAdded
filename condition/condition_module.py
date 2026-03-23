from condition.adhdCondition import generate_questions as adhd_q, calculate_severity as adhd_s
from condition.anxiety import generate_questions as anx_q, calculate_severity as anx_s
from condition.ocdCondition import generate_questions as ocd_q, calculate_severity as ocd_s
from redis import Redis
import os

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

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
    
    if redis_client:
        redis_client.set(f"user_condition:{user}", f"{condition}:{result}")

    del user_sessions[user]

    response = generate_response(condition, result)

    return f"✅ Test Completed!\n\n{response}"

def generate_response(condition, severity):
    if condition == "adhd":
        if severity == "Low likelihood":
            return "You're doing quite well with focus and attention. Keep maintaining your routines and habits 😊"
        elif severity == "Mild traits":
            return "You might experience occasional focus issues. Small changes like structured routines and task planning can really help 💡"
        elif severity == "Moderate traits":
            return "It seems like focus and organization might be challenging at times. You could benefit from strategies like breaking tasks into smaller steps and minimizing distractions. I'm here if you'd like help with that 🤝"
        else:
            return "It looks like attention and impulsivity might be affecting your daily life significantly. It could really help to talk to a professional, and I can also support you with coping strategies 💙"

    elif condition == "anxiety":
        if severity == "Minimal":
            return "Your responses suggest you're managing things quite well. Keep taking care of yourself 🌿"
        elif severity == "Mild":
            return "You might be experiencing some stress or worry. Relaxation techniques and mindful breathing can help 💡"
        elif severity == "Moderate":
            return "It seems like anxiety might be affecting you noticeably. You're not alone — grounding exercises or talking it out can really help 🤝"
        else:
            return "It seems like anxiety is quite intense right now. Please consider reaching out to a mental health professional. I'm here to support you too 💙"

    elif condition == "ocd":
        if severity == "Minimal":
            return "These thoughts or habits seem to be minimal and manageable. You're doing well 🌿"
        elif severity == "Mild":
            return "You might notice some repetitive thoughts or habits, but they seem manageable. Awareness is a great first step 💡"
        elif severity == "Moderate":
            return "It looks like these patterns might be affecting your daily routine. Gentle coping strategies can help, and I can guide you 🤝"
        else:
            return "These thoughts or behaviors seem quite distressing. It may really help to seek professional guidance. You're not alone in this 💙"