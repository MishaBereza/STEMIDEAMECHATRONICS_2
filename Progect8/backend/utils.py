def calculate_average_score(scores):
    """Return average score or 0 if empty."""
    return sum(scores) / len(scores) if scores else 0


def adjust_difficulty(current_level, average_score):
    """Adjust difficulty level based on average score.

    Rules:
    - avg > 80 : increase
    - avg < 50 and current_level > 1 : decrease
    - otherwise unchanged
    """
    if average_score > 80:
        return current_level + 1
    elif average_score < 50 and current_level > 1:
        return current_level - 1
    return current_level


def generate_new_round(current_level, scores):
    # Додаток А: аналіз середнього балу
    # (функція calculate_average_score)
    avg = calculate_average_score(scores)

    # Додаток В: адаптивний механізм зміни рівня
    # (функція adjust_difficulty)
    new_level = adjust_difficulty(current_level, avg)

    # Додаток С: генерація обʼєкту нового раунду
    return {
        "round_level": new_level,
        "average_score": avg,
        "message": f"Next round difficulty: {new_level}"
    }
