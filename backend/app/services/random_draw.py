import random


def draw_random_index(option_count: int) -> int:
    """Tire un index 1-based aléatoire dans [1, option_count].

    Seul et unique algorithme de tirage de l'application : utilisé aussi bien
    pour "l'app décide" sur une question isolée que pour "tout générer pour
    moi" (appelé une fois par question, 5 fois au total).
    """
    if option_count < 1:
        raise ValueError("option_count must be >= 1")
    return random.randint(1, option_count)
