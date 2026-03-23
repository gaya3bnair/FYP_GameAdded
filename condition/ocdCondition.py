import random


OCD_KEYWORDS = [
    "contamination fears",
    "excessive handwashing",
    "fear of germs",
    "cleaning rituals",
    "checking locks repeatedly",
    "checking appliances repeatedly",
    "fear of harming others",
    "fear of harming yourself",
    "intrusive violent thoughts",
    "intrusive sexual thoughts",
    "need for symmetry",
    "arranging objects precisely",
    "counting rituals",
    "mental reviewing",
    "seeking reassurance",
    "fear of making mistakes",
    "perfectionism",
    "repeating words silently",
    "touching objects repeatedly",
    "avoiding public places",
    "avoiding contamination triggers",
    "fear of blurting out something inappropriate",
    "religious obsessions",
    "moral scrupulosity",
    "hoarding items",
    "difficulty discarding objects",
    "superstitious rituals",
    "needing things to feel 'just right'",
    "re-reading or rewriting repeatedly",
    "mental counting",
    "washing until skin irritation",
    "checking body sensations",
    "fear of losing control",
    "excessive doubt",
    "confessing repeatedly",
    "avoidance of sharp objects",
    "time-consuming rituals",
    "distress if interrupted",
    "rigid routines",
    "fear of contamination from people",
    "repeatedly seeking certainty"
]

SCORE_OPTIONS = {
    "0": "None",
    "1": "Mild",
    "2": "Moderate",
    "3": "Severe",
    "4": "Extreme"
}

def generate_questions(num_questions=15):
    selected = random.sample(OCD_KEYWORDS, num_questions)
    return [f"How much distress or interference do you experience due to {symptom}?" 
            for symptom in selected]

def calculate_severity(score):
    if score <= 15:
        return "Minimal"
    elif score <= 30:
        return "Mild"
    elif score <= 45:
        return "Moderate"
    elif score <= 60:
        return "Severe"
    else:
        return "Extreme"

if __name__ == "__main__":
    print("\nOCD Screening ")
    print("0=None | 1=Mild | 2=Moderate | 3=Severe | 4=Extreme\n")

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
    print("OCD RESULT")
    print("==============================")
    print(f"Total Score: {total_score}/60")
    print(f"Severity Level: {severity}")
    print("==============================\n")
