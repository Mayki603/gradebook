# Процес «Виставлення оцінки» (BPMN)

Артефакт Завдання 4: `process.bpmn` (BPMN 2.0 XML), рендер — `process.svg`, `process.png` (створено з `process.bpmn`). Процес деталізує UC «Виставити оцінку» (Завдання 2). Специфікація — `spec.md` §7, ключове рішення — `adr/0005-process-form-bpmn.md`. Перевірка: `scripts/check_bpmn.py`.

## 1. Учасники

| Пул | Лейн | Хто | Походження |
|-----|------|-----|------------|
| Викладач | Викладач | людина | актор із Завдання 2 (TEACHER) |
| Електронний журнал | GradebookUI | клієнт | учасник sequence (Завдання 3) |
| Електронний журнал | GradeService | прикладний сервіс | учасник sequence (Завдання 3) |

Data Objects — сутності ER: LESSON, STUDENT, GRADE. Зовнішні системи (автентифікація — ADR 0002, п. 4; Email — «Поза обсягом») у цьому процесі не обмінюються повідомленнями, тому як чорні скриньки не показані: Викладач авторизований до початку процесу (Background у Gherkin).

## 2. Задачі

| Id | Назва | Тип | Лейн | Виклик у Sequence | Вимога |
|----|-------|-----|------|-------------------|--------|
| T_Select | Обрати своє заняття та студента групи | user | Викладач | getMyLessons, getGroupRoster | include UC |
| T_Score | Ввести бал | user | Викладач | | REQ-1 |
| T_Comment | Ввести коментар | user | Викладач | | REQ-6 |
| T_Send | Надіслати оцінку | send | Викладач | submitGrade | |
| T_Manual | Перевірити журнал пізніше | manual | Викладач | | |
| S_Forward | Передати запит сервісу оцінок | service | GradebookUI | saveGrade | |
| S_Lesson | Завантажити заняття | service | GradeService | findById (LESSON) | REQ-5 |
| S_Student | Завантажити студента | service | GradeService | findById (STUDENT) | REQ-5 |
| S_Validate | Перевірити бал | business rule | GradeService | validateScore | REQ-1 |
| S_Find | Знайти оцінку студента за заняття | service | GradeService | findByStudentAndLesson | |
| S_Update | Замінити бал в оцінці | service | GradeService | updateScore | REQ-4 |
| S_Create | Створити оцінку | service | GradeService | create | REQ-2, REQ-6 |

## 3. Шлюзи

| Id | Тип | Умови | Пара |
|----|-----|-------|------|
| T_GwComment | Exclusive | «так»: wantsComment; «ні»: default | T_Merge2 |
| T_Merge1 | Exclusive (злиття) | старт і повернення на виправлення балу | |
| S_ParSplit | Parallel | заняття ‖ студент | S_ParJoin |
| S_GwAccess | Exclusive | «доступ є»: LESSON.teacher_id і STUDENT.group_id; default: AccessDenied | кінець |
| S_GwScore | Exclusive | «допустимий»: ціле 0..100; default: ValidationError | кінець |
| S_GwExists | Exclusive | «існує»: grade != null; default: створення | кінці |
| T_Wait | Event-based | GradeSaved, GradeUpdated, ValidationError, AccessDenied або таймер | кінці, повернення |

## 4. Повідомлення

| Повідомлення | Відправник → отримувач | Елемент BPMN | Чи чекає відправник | Якщо відповіді немає | Sequence (Завдання 3) |
|--------------|------------------------|--------------|---------------------|----------------------|------------------------|
| submitGrade | Викладач → GradebookUI | send task → message start event | так (T_Wait) | таймер 10 с → Викладач перевіряє журнал пізніше | `T->>UI: submitGrade` |
| GradeSaved | GradebookUI → Викладач | message end event → catch event | ні, шлях системи завершується | не застосовно: отримувач чекає на T_Wait | `GS-->>UI: GradeSaved` |
| GradeUpdated | GradebookUI → Викладач | те саме | ні | те саме | `GS-->>UI: GradeUpdated` |
| ValidationError | GradebookUI → Викладач | те саме | ні | те саме | `GS-->>UI: ValidationError` |
| AccessDenied | GradebookUI → Викладач | те саме | ні | те саме | `GS-->>UI: AccessDenied` |

## 5. Сценарії → шляхи

| Сценарій | Шлях (рішення на шлюзах) | Кінець |
|----------|--------------------------|--------|
| S1 | коментаря немає → доступ є → бал допустимий → оцінки немає | GradeSaved, «Оцінку збережено» |
| S2 | коментаря немає → доступ є → бал некоректний | ValidationError, повернення до «Ввести бал» |
| S3 | коментаря немає → доступ є → бал допустимий → оцінка існує | GradeUpdated, «Оцінку змінено» |
| S4 | коментаря немає → доступу немає | AccessDenied, «Відмовлено в доступі» |
| S5 | коментар є → доступ є → бал допустимий → оцінки немає | GradeSaved, «Оцінку збережено» |

## 6. Шляхи без Gherkin-сценарію

Не розглядалося.

## 7. Для перевірки скриптом

```json
{
  "scenarios": {
    "S1": {
      "decisions": [
        "F_T6",
        "F_S8",
        "F_S11",
        "F_S15"
      ],
      "reach": [
        "S_Create",
        "S_EndSaved",
        "T_CatchSaved",
        "T_EndSaved"
      ],
      "avoid": [
        "S_Update"
      ]
    },
    "S2": {
      "decisions": [
        "F_T6",
        "F_S8",
        "F_S12"
      ],
      "reach": [
        "S_EndInvalid",
        "T_CatchInvalid"
      ],
      "avoid": [
        "S_Create",
        "S_Update"
      ]
    },
    "S3": {
      "decisions": [
        "F_T6",
        "F_S8",
        "F_S11",
        "F_S14"
      ],
      "reach": [
        "S_Update",
        "S_EndUpdated",
        "T_CatchUpdated",
        "T_EndUpdated"
      ],
      "avoid": [
        "S_Create"
      ]
    },
    "S4": {
      "decisions": [
        "F_T6",
        "F_S9"
      ],
      "reach": [
        "S_EndDenied",
        "T_CatchDenied",
        "T_EndDenied"
      ],
      "avoid": [
        "S_Validate",
        "S_Find",
        "S_Create",
        "S_Update"
      ]
    },
    "S5": {
      "decisions": [
        "F_T5",
        "F_S8",
        "F_S11",
        "F_S15"
      ],
      "reach": [
        "T_Comment",
        "S_Create",
        "T_EndSaved"
      ],
      "avoid": [
        "S_Update"
      ]
    }
  },
  "justified": []
}
```