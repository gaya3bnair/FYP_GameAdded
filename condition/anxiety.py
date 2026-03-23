import random

ANXIETY_KEYWORDS = [
    "excessive worry",
    "difficulty controlling worry",
    "restlessness",
    "muscle tension",
    "sleep disturbance",
    "irritability",
    "feeling on edge",
    "panic attacks",
    "heart palpitations",
    "shortness of breath",
    "sweating",
    "trembling",
    "fear of losing control",
    "anticipatory anxiety",
    "social fear",
    "avoidance of social situations",
    "catastrophic thinking",
    "fear of embarrassment",
    "difficulty concentrating due to worry",
    "digestive discomfort from anxiety",
    "headaches due to stress",
    "fatigue",
    "overthinking",
    "fear of negative evaluation",
    "hypervigilance",
    "difficulty relaxing",
    "chest tightness",
    "feeling detached",
    "sudden intense fear",
    "nausea from anxiety",
    "fear of uncertainty",
    "health anxiety",
    "avoidance behaviors",
    "constant sense of dread",
    "rumination",
    "fear of something bad happening",
    "shakiness",
    "difficulty making decisions due to worry",
    "insomnia from anxious thoughts",
    "fear of public speaking",
    "avoidance of stressful tasks"
]

SCORE_OPTIONS = {
    "0": "Not at all",
    "1": "Occasionally",
    "2": "Sometimes",
    "3": "Frequently",
    "4": "Almost Constantly"
}

def generate_questions(num_questions=15):
    selected = random.sample(ANXIETY_KEYWORDS, num_questions)
    return [f"How often have you experienced {symptom} in the past two weeks?" 
            for symptom in selected]

def calculate_severity(score):
    if score <= 15:
        return "Minimal"
    elif score <= 30:
        return "Mild"
    elif score <= 45:
        return "Moderate"
    else:
        return "Severe"

if __name__ == "__main__":
    print("\nAnxiety Screening\n")
    print("0=Not at all | 1=Occasionally | 2=Sometimes | 3=Frequently | 4=Almost Constantly\n")

    questions = generate_questions()
    total_score = 0

    for i, q in enumerate(questions, 1):
        print(f"Q{i}. {q}")
        while True:
            ans = input("Score (0-4): ").strip()
            if ans in SCORE_OPTIONS:
                total_score += int(ans)
                break
            else:
                print("Enter 0-4.")
        print()

    severity = calculate_severity(total_score)

    print("\n==============================")
    print("ANXIETY RESULT")
    print("==============================")
    print(f"Total Score: {total_score}/60")
    print(f"Severity Level: {severity}")
    print("==============================\n")