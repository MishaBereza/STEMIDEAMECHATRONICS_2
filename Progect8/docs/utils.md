# utils.py

## Призначення
Допоміжні обчислювальні функції для adaptive difficulty та роботи з оцінками команд.

## Функції

### calculate_average_score(scores)
- Аргумент: список чисел
- Повертає: середнє значення, або 0 якщо список порожній

### adjust_difficulty(current_level, average_score)
- Параметри:
  - current_level (int)
  - average_score (float)
- Правила:
  - avg > 80 → level + 1
  - avg < 50 і current_level > 1 → level - 1
  - інакше → поточний рівень

### generate_new_round(current_level, scores)
- Обчислює `avg` за `scores`
- Викликає `adjust_difficulty`
- Повертає словник із ключами:
  - `round_level`
  - `average_score`
  - `message`
