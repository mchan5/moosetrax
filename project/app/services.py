def analyze_text(text: str):
    # pretend ML / logic
    score = min(len(text) / 100, 1.0)

    return {
        "confidence": score,
        "note": "Longer input → higher confidence"
    }
