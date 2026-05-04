# EduTrack: Student Attendance & Performance Dashboard

EduTrack is a Flask + SQLite web application for teachers to manage student attendance and marks, detect low-attendance students, and generate subject-wise performance reports.

## Features

- Teacher login
- Add and search students
- Mark subject-wise attendance by date
- Add subject-wise marks by exam
- View low-attendance students by threshold
- Generate subject-wise attendance and marks reports
- SQL analytics dashboard
- SQLite database created automatically with seed data

## Run Locally

```powershell
cd edutrack
python -m pip install flask werkzeug
python app.py
```

Open `http://127.0.0.1:5003`.

## Demo Account

- Username: `teacher`
- Password: `teacher123`

## Resume Line

Built EduTrack, a Flask and SQLite attendance and performance dashboard for teachers with student management, attendance marking, marks entry, low-attendance alerts, and SQL-based subject reports.
