# Лог генерації ER-діаграми

## Prompt 1
**Запит до AI:** Зроби концептуальну ER-діаграму у форматі Mermaid для системи "Електронний журнал". Сутності: STUDENT, GROUP, TEACHER, COURSE, LESSON, GRADE.

**Відповідь AI (первинна, сира):**
```mermaid
erDiagram
    GROUP { int id string name }
    STUDENT { int id string name int group_id }
    TEACHER { int id string name }
    COURSE { int id string name }
    LESSON { int id int course_id }
    GRADE { int id int score }
    GROUP ||--o{ STUDENT : has
    TEACHER ||--o{ COURSE : has
    STUDENT ||--o{ GRADE : has