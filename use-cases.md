# Вимоги та Сценарії використання

## 1. Функціональні вимоги (EARS)
- **REQ-1:** WHEN a TEACHER submits a new GRADE for a STUDENT, the system SHALL validate the score constraints (0-100).
- **REQ-2:** WHILE a new GRADE is successfully saved, the Email-Service SHALL trigger a notification to the STUDENT's email.
- **REQ-3:** WHEN a STUDENT requests their academic record, the system SHALL display a list of all their associated GRADEs.
- **REQ-4 (Непокрита):** WHERE the system detects suspicious login attempts, it SHALL temporarily lock the TEACHER's account.

## 2. Нефункціональні вимоги (NFR)
- **NFR-1 (Performance):** Система SHALL забезпечувати час відгуку < 1.5 секунди при навантаженні до 1000 одночасних запитів.
- **NFR-2 (Security):** Система SHALL використовувати алгоритм AES-256 для шифрування бази даних та JWT-токени (термін дії 1 година) для авторизації TEACHER.
- **NFR-3 (Usability/Tech):** Веб-інтерфейс SHALL коректно відображатися на мобільних пристроях (iOS 15+, Android 10+) з використанням React.js.

## 3. Gherkin-сценарії (Складний UC: Управління оцінками)
**Feature: Управління оцінками** (Як викладач, я хочу виставляти оцінки, щоб фіксувати успішність)

```gherkin
# Сценарій 1: Успішне додавання оцінки (Базовий)
Scenario: Викладач успішно додає оцінку
  Given викладач авторизований та знаходиться на сторінці заняття
  When викладач ставить оцінку "95" студенту
  Then система зберігає запис GRADE
  And Email-сервіс надсилає сповіщення студенту

# Сценарій 2: Помилка валідації оцінки (Негативний)
Scenario: Викладач намагається додати некоректну оцінку
  Given викладач авторизований та знаходиться на сторінці заняття
  When викладач вводить бал "150"
  Then система відхиляє введення
  And показує помилку "Оцінка має бути від 0 до 100"

# Сценарій 3: Оновлення оцінки (Альтернативний)
Scenario: Викладач змінює існуючу оцінку
  Given викладач раніше вже виставив GRADE студенту
  When викладач оновлює бал з "95" на "100"
  Then система оновлює запис GRADE
  And зберігає зміну в історії журналу
```

## 4. Use Case Діаграма (Mermaid)
```mermaid
flowchart LR
    User([User])
    Teacher([TEACHER])
    Student([STUDENT])
    EmailSys[[Email-Service]]
    
    Teacher --|> User
    Student --|> User

    Auth(Authenticate)
    AddGrade(Add GRADE)
    ViewGrades(View GRADEs)
    SendEmail(Send Notification)
    Export(Export Report)

    Teacher --> AddGrade
    Student --> ViewGrades
    EmailSys --> SendEmail

    AddGrade -. "include" .-> Auth
    ViewGrades -. "include" .-> Auth
    AddGrade -. "include" .-> SendEmail
    ViewGrades <.. "extend" .. Export
```

## 5. Матриця трасування
| Вимога (EARS) | Gherkin-сценарій | Примітка |
|---------------|------------------|----------|
| REQ-1  | Сценарій 1, Сценарій 2 | Валідація та успішне збереження (M:N) |
| REQ-2  | Сценарій 1 | Зв'язок з Email-сервісом |
| REQ-3  | - | Покривається іншим UC (View Grades) |
| REQ-4  | - | **Непокрита:** Функціонал безпеки поза MVP. |