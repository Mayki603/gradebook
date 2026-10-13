# DEFENSE — Завдання 1: Домен і модель даних (ER)

**Намір і критерії:** 
Спроєктувати ER-діаграму відповідно до 3NF. 
- **Чому цей домен:** "Електронний журнал" чітко відображає реальні бізнес-процеси (взаємодія студентів, груп, викладачів та занять).
- **Чому 3NF:** Усі сутності мають PK (`id`), неключові атрибути залежать виключно від ключа, відсутні транзитивні залежності.

**Топ-3 розбіжності (аудит) та SHA комітів-виправлень:**
1. **Типи даних та відсутні ключі:** AI спочатку видав типи `int` та пропустив позначки ключів. Виправлено на концептуальні типи з PK/FK "UUID". (Виправлено в коміті: 1d6f199)
2. **Загальні назви зв'язків:** AI використав слово `has` для всіх зв'язків. Виправлено на точні дієслова. (Виправлено в коміті: e0a244e)
3. **Пропущені зв'язки:** AI у сирій версії не пов'язав `LESSON` з іншими сутностями. Усі відношення для заняття були успішно додані. (Виправлено в коміті: e0a244e)

**Ключове рішення (ADR):** Прямий зв'язок M:N для TEACHER-COURSE, та `GRADE` як асоціативна сутність. Деталі в ADR 0001.

---
### Рендер фінальної діаграми:
```mermaid
erDiagram
    GROUP {
        string id PK "UUID"
        string name
        number enrollment_year
    }
    STUDENT {
        string id PK "UUID"
        string name
        string email
        string group_id FK "UUID"
    }
    TEACHER {
        string id PK "UUID"
        string name
        string email
        string department
    }
    COURSE {
        string id PK "UUID"
        string name
        number credits
    }
    LESSON {
        string id PK "UUID"
        string course_id FK "UUID"
        string teacher_id FK "UUID"
        string group_id FK "UUID"
        date date
        string topic
    }
    GRADE {
        string id PK "UUID"
        string student_id FK "UUID"
        string lesson_id FK "UUID"
        number score
        string grade_type
        string comment
    }

    GROUP ||--o{ STUDENT : "contains"
    GROUP ||--o{ LESSON : "attends"
    TEACHER }|--|{ COURSE : "teaches"
    TEACHER ||--o{ LESSON : "conducts"
    COURSE ||--o{ LESSON : "includes"
    STUDENT ||--o{ GRADE : "receives"
    LESSON ||--o{ GRADE : "results_in"