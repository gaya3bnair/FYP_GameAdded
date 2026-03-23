import random

ADHD_KEYWORDS = [
    "difficulty sustaining attention",
    "careless mistakes",
    "difficulty organizing tasks",
    "avoiding long mental effort",
    "losing important items",
    "forgetting appointments",
    "procrastination",
    "difficulty finishing tasks",
    "easily distracted",
    "mind wandering",
    "restlessness",
    "fidgeting",
    "difficulty sitting still",
    "talking excessively",
    "interrupting others",
    "impatience",
    "acting impulsively",
    "difficulty waiting turn",
    "blurting out answers",
    "poor time management",
    "frequent boredom",
    "difficulty prioritizing",
    "starting tasks but not completing them",
    "misplacing keys or phone",
    "difficulty following instructions",
    "zoning out during conversations",
    "forgetting daily responsibilities",
    "hyperfocus on certain tasks",
    "mood swings",
    "difficulty managing emotions",
    "avoiding detailed work",
    "difficulty reading long texts",
    "frequent job changes",
    "driving impulsively",
    "forgetting deadlines",
    "poor academic performance",
    "trouble maintaining routines",
    "difficulty multitasking",
    "overcommitting",
    "poor listening skills",
    "daydreaming excessively"
]

SCORE_OPTIONS = {
    "0": "Never",
    "1": "Rarely",
    "2": "Sometimes",
    "3": "Often",
    "4": "Very Often"
}

def generate_questions(num_questions=15):
    selected = random.sample(ADHD_KEYWORDS, num_questions)
    return [f"How often do you experience {symptom}?" for symptom in selected]

def calculate_severity(score):
    if score <= 15:
        return "Low likelihood"
    elif score <= 30:
        return "Mild traits"
    elif score <= 45:
        return "Moderate traits"
    else:
        return "High likelihood"

if __name__ == "__main__":
    print("\nADHD Screening\n")
    print("0=Never | 1=Rarely | 2=Sometimes | 3=Often | 4=Very Often\n")

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
    print("ADHD RESULT")
    print("==============================")
    print(f"Total Score: {total_score}/60")
    print(f"Assessment: {severity}")
    print("==============================\n")
