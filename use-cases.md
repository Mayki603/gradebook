# Вимоги та Сценарії використання

## 1. EARS-вимоги
- **REQ-1:** WHEN a TEACHER submits a new GRADE for a STUDENT, the system SHALL validate the score constraints.
- **REQ-2:** WHILE a new GRADE is successfully saved, the Email-Service SHALL trigger a notification to the STUDENT's email.
- **REQ-3:** WHEN a STUDENT requests their academic record, the system SHALL display a list of all their associated GRADEs.
- **REQ-4 (Непокрита):** WHERE the system detects suspicious login attempts, it SHALL temporarily lock the TEACHER's account.

## 2. User Stories
- **US-1:** As a TEACHER, I want to add grades for a lesson, so that student progress is recorded.
- **US-2:** As a STUDENT, I want to view my grade history, so that I can track my academic performance.
- **US-3:** As a TEACHER, I want the system to email students automatically, so that I don't have to notify them manually.

## 3. Gherkin-сценарії
**Feature: Grade Management**
```gherkin
Scenario: TEACHER successfully adds a grade
  Given the TEACHER is authenticated and viewing the LESSON page
  When the TEACHER assigns a score of "95" to a STUDENT
  Then the system saves the GRADE
  And the Email-Service sends a notification to the STUDENT
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
| Вимога | Сценарії (User Stories) | Примітка |
|--------|-------------------------|----------|
| REQ-1  | US-1                    |          |
| REQ-2  | US-1, US-3              | Зв'язок M:N |
| REQ-3  | US-2                    |          |
| REQ-4  | -                       | **Непокрита:** Функціонал безпеки виходить за межі MVP-версії електронного журналу та буде реалізований у наступних спринтах. |