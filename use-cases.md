# Вимоги та Сценарії використання

## 1. EARS-вимоги
- **REQ-1:** WHEN a Tutor grades a Pupil, the system SHALL quickly save the mark.
- **REQ-2:** WHILE the system is working, it SHALL send emails to students sometimes.
- **REQ-3:** WHEN a Pupil opens the system, they SHALL see their grades easily.

## 2. User Stories
- **US-1:** As a Tutor, I want to add grades, so that Pupils know their results.
- **US-2:** As a Pupil, I want to view my grades.

## 3. Gherkin-сценарії
**Feature: Grading**
Scenario: Tutor adds a grade
  Given the Tutor is on the grading page
  When the Tutor enters a good grade
  Then the system saves it

## 4. Use Case Діаграма (Mermaid)
```mermaid
flowchart LR
    A1([Tutor])
    A2([Pupil])
    
    UC1(Add Grade)
    UC2(View Grades)
    
    A1 --> UC1
    A2 --> UC2