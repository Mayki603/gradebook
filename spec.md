# Специфікація: Доменна модель електронного журналу

## 1. Сутності та атрибути
- STUDENT: id, name, email, group_id
- GROUP: id, name, enrollment_year
- TEACHER: id, name, email, department
- COURSE: id, name, credits
- LESSON: id, course_id, teacher_id, group_id, date, topic
- GRADE: id, student_id, lesson_id, score, grade_type, comment

## 2. Зв'язки між сутностями (словами)
- Студент (STUDENT) належить одній групі (GROUP).
- Група (GROUP) містить багато студентів (STUDENT) та відвідує багато занять (LESSON).
- Викладач (TEACHER) викладає багато предметів (COURSE) та проводить багато занять (LESSON).
- Предмет (COURSE) викладається багатьма викладачами (TEACHER).
- Заняття (LESSON) належить до одного предмета (COURSE), проводиться одним викладачем (TEACHER) для однієї групи (GROUP).
- Оцінка (GRADE) отримується одним студентом (STUDENT) за одне заняття (LESSON).