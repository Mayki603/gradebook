# Взаємодія: Sequence-діаграми сценаріїв UC «Виставити оцінку»

Джерела: сценарії S1–S6 і вимоги REQ-1…REQ-7 — `use-cases.md` (Завдання 2); сутності й поля — `er-diagram.mmd` (Завдання 1).

**Припущення детальнішого рівня** (не змінюють вимоги Завдання 2): A1 — список групи показує поточну оцінку за заняття (потрібно для S3); A2 — `grade_type` при створенні має значення за замовчуванням (ADR 0002, п. 5). Деталі — `spec.md` §6, ADR 0004.

**Учасники.** Викладач / Студент — актори (TEACHER / STUDENT з ER); `GradebookUI` — клієнт; `GradeService` — прикладний сервіс; `LESSON`, `STUDENT`, `GRADE` — сутності ER (доступ до даних).

## S1. Викладач успішно додає валідну оцінку

Gherkin: Background «викладач авторизований» → «обирає своє заняття та студента групи» → «вводить бал "95"» → «система створює запис GRADE з балом "95"». Вимоги: REQ-1, REQ-2, REQ-5.

```mermaid
sequenceDiagram
    autonumber
    actor T as Викладач
    participant UI as GradebookUI
    participant GS as GradeService
    participant L as LESSON
    participant S as STUDENT
    participant G as GRADE

    Note over UI,GS: Given: викладач авторизований, teacherId відомий із сесії
    T->>UI: openJournal()
    activate UI
    UI->>GS: getMyLessons(teacherId)
    activate GS
    GS->>+L: findByTeacher(teacherId)
    L-->>-GS: lessons (id, group_id, topic, date)
    GS-->>UI: lessons
    deactivate GS
    UI-->>T: показує список власних занять

    T->>UI: selectLesson(lessonId)
    UI->>GS: getGroupRoster(lessonId)
    activate GS
    GS->>+L: findById(lessonId)
    L-->>-GS: lesson (group_id)
    GS->>+S: findByGroup(group_id)
    S-->>-GS: students (id, name)
    loop для кожного студента групи (припущення A1)
        GS->>+G: findByStudentAndLesson(studentId, lessonId)
        G-->>-GS: поточна оцінка або порожньо
    end
    GS-->>UI: roster (students, currentScores)
    deactivate GS
    UI-->>T: показує склад групи
    deactivate UI

    T->>UI: submitGrade(studentId, score = 95)
    activate UI
    UI->>GS: saveGrade(teacherId, lessonId, studentId, 95, null)
    activate GS
    par завантажити заняття
        GS->>+L: findById(lessonId)
        L-->>-GS: lesson (teacher_id, group_id)
    and завантажити студента
        GS->>+S: findById(studentId)
        S-->>-GS: student (group_id)
    end
    alt LESSON.teacher_id = teacherId і STUDENT.group_id = LESSON.group_id
        GS->>GS: validateScore(95)
        alt бал — ціле число від 0 до 100
            GS->>+G: findByStudentAndLesson(studentId, lessonId)
            G-->>-GS: запису немає
            Note over GS,G: grade_type — значення за замовчуванням (припущення A2)
            GS->>+G: create(studentId, lessonId, 95, null, gradeTypeDefault)
            G-->>-GS: grade (id, score = 95)
            GS-->>UI: GradeSaved(gradeId)
            UI-->>T: показує підтвердження збереження
        else бал некоректний — сценарій S2
            GS-->>UI: ValidationError
            UI-->>T: показує помилку валідації
        end
    else доступ заборонено — сценарій S4
        GS-->>UI: AccessDenied
        UI-->>T: показує помилку доступу
    end
    deactivate GS
    deactivate UI
```

## S2. Викладач вводить некоректний бал

Gherkin (Scenario Outline): бал "150" / "-1" / "95.5" → «система відхиляє збереження» → помилка "Оцінка має бути від 0 до 100" → «запис GRADE не створюється і не змінюється». Вимоги: REQ-1, REQ-3.

```mermaid
sequenceDiagram
    autonumber
    actor T as Викладач
    participant UI as GradebookUI
    participant GS as GradeService
    participant L as LESSON
    participant S as STUDENT
    participant G as GRADE

    Note over UI,GS: Given: викладач авторизований. Вибір заняття та студента — як у S1
    T->>UI: submitGrade(studentId, score)
    Note right of T: приклади score: 150, -1, 95.5
    activate UI
    UI->>GS: saveGrade(teacherId, lessonId, studentId, score, null)
    activate GS
    par завантажити заняття
        GS->>+L: findById(lessonId)
        L-->>-GS: lesson (teacher_id, group_id)
    and завантажити студента
        GS->>+S: findById(studentId)
        S-->>-GS: student (group_id)
    end
    GS->>GS: checkAccess(teacherId, lesson, student)
    GS->>GS: validateScore(score)
    alt бал не є цілим числом від 0 до 100
        GS-->>UI: ValidationError("Оцінка має бути від 0 до 100")
        UI-->>T: показує помилку "Оцінка має бути від 0 до 100"
        Note over G: GRADE не викликається — запис не створюється й не змінюється
    else бал валідний
        Note over GS,G: збереження — сценарії S1, S3
    end
    deactivate GS
    deactivate UI
```

## S3. Викладач змінює вже виставлену оцінку

Gherkin: «студент вже має оцінку "90" за це заняття» → «вводить новий бал "95"» → «система замінює бал на "95" в наявному записі GRADE» → «новий запис GRADE не створюється». Вимоги: REQ-1, REQ-4.

```mermaid
sequenceDiagram
    autonumber
    actor T as Викладач
    participant UI as GradebookUI
    participant GS as GradeService
    participant L as LESSON
    participant S as STUDENT
    participant G as GRADE

    Note over UI,GS: Given: викладач авторизований, студент уже має оцінку 90 за це заняття
    Note over UI,GS: Вибір заняття та студента — як у S1 (у списку групи поточна оцінка 90)
    T->>UI: submitGrade(studentId, score = 95)
    activate UI
    UI->>GS: saveGrade(teacherId, lessonId, studentId, 95, null)
    activate GS
    par завантажити заняття
        GS->>+L: findById(lessonId)
        L-->>-GS: lesson (teacher_id, group_id)
    and завантажити студента
        GS->>+S: findById(studentId)
        S-->>-GS: student (group_id)
    end
    GS->>GS: checkAccess(teacherId, lesson, student)
    GS->>GS: validateScore(95)
    GS->>+G: findByStudentAndLesson(studentId, lessonId)
    G-->>-GS: grade (id, score = 90)
    alt запис GRADE уже існує
        GS->>+G: updateScore(gradeId, 95)
        G-->>-GS: grade (id, score = 95)
        GS-->>UI: GradeUpdated(gradeId)
        UI-->>T: показує підтвердження зміни
        Note over G: новий запис GRADE не створюється
    else запису немає
        Note over GS,G: створення нового запису — сценарій S1
    end
    deactivate GS
    deactivate UI
```

## S4. Викладач намагається виставити оцінку без доступу

Gherkin (Scenario Outline): «студент іншої групи» за «своє заняття» / «студент групи заняття» за «заняття іншого викладача» → «система відхиляє збереження» → помилка доступу "Немає доступу до цього заняття або студента". Вимога: REQ-5.

```mermaid
sequenceDiagram
    autonumber
    actor T as Викладач
    participant UI as GradebookUI
    participant GS as GradeService
    participant L as LESSON
    participant S as STUDENT
    participant G as GRADE

    Note over UI,GS: Given: викладач авторизований
    T->>UI: submitGrade(studentId, score = 85)
    Note right of T: приклади: студент іншої групи, заняття іншого викладача
    activate UI
    UI->>GS: saveGrade(teacherId, lessonId, studentId, 85, null)
    activate GS
    par завантажити заняття
        GS->>+L: findById(lessonId)
        L-->>-GS: lesson (teacher_id, group_id)
    and завантажити студента
        GS->>+S: findById(studentId)
        S-->>-GS: student (group_id)
    end
    alt LESSON.teacher_id не збігається з teacherId
        GS-->>UI: AccessDenied("Немає доступу до цього заняття або студента")
        UI-->>T: показує помилку доступу
    else STUDENT.group_id не збігається з LESSON.group_id
        GS-->>UI: AccessDenied("Немає доступу до цього заняття або студента")
        UI-->>T: показує помилку доступу
    else доступ підтверджено
        Note over GS,G: перевірка балу й збереження — сценарії S1–S3
    end
    Note over G: GRADE не викликається — нічого не створюється й не змінюється
    deactivate GS
    deactivate UI
```

## S5. Викладач додає коментар до оцінки (extend)

Gherkin: «вводить бал "95" і коментар "Відмінна робота"» → «система створює запис GRADE з балом "95" і коментарем "Відмінна робота"». Вимоги: REQ-1, REQ-2, REQ-6.

```mermaid
sequenceDiagram
    autonumber
    actor T as Викладач
    participant UI as GradebookUI
    participant GS as GradeService
    participant L as LESSON
    participant S as STUDENT
    participant G as GRADE

    Note over UI,GS: Given: викладач авторизований. Вибір заняття та студента — як у S1
    T->>UI: enterScore(studentId, score = 95)
    activate UI
    opt Викладач додає коментар (extend UC)
        T->>UI: enterComment("Відмінна робота")
        UI->>UI: attachComment(comment)
    end
    UI->>GS: saveGrade(teacherId, lessonId, studentId, 95, "Відмінна робота")
    activate GS
    par завантажити заняття
        GS->>+L: findById(lessonId)
        L-->>-GS: lesson (teacher_id, group_id)
    and завантажити студента
        GS->>+S: findById(studentId)
        S-->>-GS: student (group_id)
    end
    GS->>GS: checkAccess(teacherId, lesson, student)
    GS->>GS: validateScore(95)
    GS->>+G: findByStudentAndLesson(studentId, lessonId)
    G-->>-GS: запису немає
    Note over GS,G: grade_type — значення за замовчуванням (припущення A2)
    GS->>+G: create(studentId, lessonId, 95, "Відмінна робота", gradeTypeDefault)
    G-->>-GS: grade (id, score = 95, comment)
    GS-->>UI: GradeSaved(gradeId)
    UI-->>T: показує підтвердження збереження
    deactivate GS
    deactivate UI
```

## S6. Студент запитує оцінки іншого студента (UC «Переглянути успішність», доступ)

Gherkin: «студент відкриває оцінки іншого студента» → «система відповідає 403» → «жодна оцінка іншого студента не повертається». Вимога: REQ-7.

```mermaid
sequenceDiagram
    autonumber
    actor ST as Студент
    participant UI as GradebookUI
    participant GS as GradeService
    participant G as GRADE

    Note over UI,GS: Given: студент авторизований, currentStudentId відомий із сесії
    ST->>UI: openGrades(requestedStudentId)
    activate UI
    UI->>GS: getGrades(currentStudentId, requestedStudentId)
    activate GS
    alt requestedStudentId не збігається з currentStudentId
        GS-->>UI: Forbidden(403)
        UI-->>ST: показує помилку доступу
        Note over G: GRADE не викликається — жодна оцінка не повертається
    else студент запитує власні оцінки
        GS->>+G: findByStudent(currentStudentId)
        G-->>-GS: grades (lesson_id, score, comment)
        GS-->>UI: grades
        UI-->>ST: показує власні оцінки
    end
    deactivate GS
    deactivate UI
```

## Трасування кроків Gherkin → повідомлення діаграм

| Сценарій | Крок Gherkin | Повідомлення на діаграмі |
|----------|--------------|--------------------------|
| S1 | обирає своє заняття та студента групи | `openJournal()`, `getMyLessons()`, `selectLesson()`, `getGroupRoster()` |
| S1 | вводить бал "95" | `submitGrade()`, `saveGrade()`, `validateScore()` |
| S1 | система створює запис GRADE | `findByStudentAndLesson()` → `create()` → `GradeSaved` |
| S2 | вводить бал "150" / "-1" / "95.5" | `submitGrade()`, `saveGrade()`, `validateScore()` |
| S2 | відхиляє збереження, показує помилку | `ValidationError("Оцінка має бути від 0 до 100")` |
| S2 | запис GRADE не створюється і не змінюється | `GRADE` не викликається |
| S3 | студент вже має оцінку "90" | `findByStudentAndLesson()` → `grade (score = 90)` |
| S3 | вводить новий бал "95" | `submitGrade()`, `saveGrade()` |
| S3 | замінює бал в наявному записі | `updateScore(gradeId, 95)` → `GradeUpdated` |
| S4 | виставляє бал студенту / за заняття без доступу | `saveGrade()`, `findById()` (LESSON, STUDENT) |
| S4 | відхиляє збереження з помилкою доступу | `AccessDenied("Немає доступу до цього заняття або студента")` |
| S5 | вводить бал "95" і коментар | `enterScore()`, `enterComment()` у фрагменті `opt` |
| S5 | створює запис GRADE з коментарем | `create(…, "Відмінна робота", …)` → `GradeSaved` |
| S6 | відкриває оцінки іншого студента | `openGrades(requestedStudentId)`, `getGrades()` |
| S6 | відповідає 403, оцінки не повертаються | `Forbidden(403)`, `GRADE` не викликається |