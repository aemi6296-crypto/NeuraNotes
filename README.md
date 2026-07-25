# NeuraNotes

#### Video Demo: https://youtu.be/2M-Og2kaawA

#### Description:

NeuraNotes is a personal study tracker website that I built as my final project for CS50. As a student, I always found it hard to keep track of everything at once which subjects I was studying, how much progress I'd actually made in each one, how much time I was really spending studying (as opposed to how much time I *thought* I was spending), and where my notes for each topic ended up. Half the time my notes were spread across random notebooks, my phone's notes app, and old messages to myself. So I decided to build something that puts all of it in one place, and I made it for my own use first, which is honestly why a lot of the features exist.

It's built with **Flask** (Python) for the backend, **SQLite** for the database, and plain **HTML, CSS, and JavaScript** for the frontend no extra frameworks on the frontend, just vanilla code. Every user has their own login, so all subjects, notes, flashcards, goals, and study history are private to that account.

## Features

**User Accounts**
Users register and log in with a username and password. Passwords go through Werkzeug's hashing before they're saved, so nothing is ever stored in plain text. If login details are wrong, the app shows an error instead of just failing silently.

**Dashboard**
The first thing you see after logging in. Shows total subjects, active goals, a quick list of your subjects with progress bars, and your active goals so you don't have to go digging for them.

**Subjects**
You can add a subject (say, Physics), give it a color so it's easy to spot at a glance, and set how many topics it has in total. You can also delete a subject if you added it by mistake or typed something wrong no need to leave junk data sitting around.

**Notes**
Inside a subject, you can write notes with a title and content, and attach an image if you want. A few things I added here that I personally wanted:
- A **search bar** that filters your notes live as you type the title no need to scroll through everything to find one note.
- **Headings and a highlighter option** while writing, so notes don't end up as one long wall of plain text.
- A proper **save** step, and a **delete** option with a confirmation popup so you don't lose a note by accident.
- **Export to PDF**, so a note can be downloaded and printed or read offline later.

**Flashcards**
This one took the longest to build. Under each subject, you can create your own flashcards, then take a quiz using them. At the end of the quiz you get a result showing how you did. If a set of results (or a flashcard) isn't useful anymore, you can delete it.

**Progress Tracking**
You update how many topics you've completed for a subject, and the progress bar recalculates on its own.

**Pomodoro Timer**
Instead of typing in "I studied for 45 minutes" by hand (which, let's be honest, people just guess), there's a Pomodoro-style timer 60 minutes of focus with short/break options. When a session finishes, it logs the time automatically and keeps a running count of sessions and a study streak.

**Study Analytics**
A separate page with a chart showing study time across different days, built from the actual logged study sessions. It's mainly there so you can see if you're actually being consistent or just think you are.

**Goals**
Add a goal with a title, target hours, and a deadline, and mark it complete once it's done. Active goals show up right on the dashboard.

**Sidebar Navigation & Logout**
A sidebar lets you move between Dashboard, Subjects, and Goals without needing to go back every time, and it collapses into a hamburger menu on smaller screens. Logout is available from there too.

**Mobile Friendly**
I wanted to actually use this from my phone, not just my laptop, so I made sure the layout including the sidebar and the analytics chart reflows properly on smaller screens instead of breaking or overlapping.

## File Structure

- **`app.py`** the main Flask app. All the routes live here: auth (register/login/logout), the dashboard, subjects (add/delete), notes (add/view/delete/search/export as PDF), flashcards (create/quiz/results/delete), goals (add/complete), logging study sessions, updating progress, and the analytics data route.

- **`init_db.py`** sets up the SQLite database and creates all the tables (`users`, `subjects`, `notes`, `goals`, `study_sessions`, and the flashcard-related tables). Only needs to be run once.

- **`neuranotes.db`** - the actual database file where everything gets stored.

- **`templates/`** - all the HTML pages:
  - `layout.html`- the base layout every page extends, with the sidebar and hamburger menu logic.
  - `index.html` - dashboard.
  - `login.html` / `register.html` — auth pages.
  - `subjects.html` - add/view/delete subjects.
  - `notes.html` - the page for a subject: progress update, Pomodoro timer, note form (with headings/highlighter), search bar, and the notes list with delete/export options.
  - `flashcards.html`, `flashcard_manage.html`, `flashcard_quiz.html` — creating flashcards, managing them, and taking the quiz with results.
  - `goals.html` - add/view/complete goals.
  - `analytics.html` - the study time chart.

- **`static/`** - `styles.css` for all the styling/colors/layout/responsiveness, plus an `uploads/` folder for note images.

- **`add_flashcards.py`** - helper script for handling flashcard creation logic separately from the main app file.

- **`add_image.py`** - helper script for validating and saving uploaded note images.

## Design Choices

I went with **Flask + SQLite** instead of something heavier because this is really a personal tool for one user's own data SQLite was more than enough and made local development a lot simpler.

For the **Pomodoro timer**, I made it log time automatically instead of having the user type in minutes, since manual logging is easy to fudge or just forget. Tying it straight to the database made the analytics actually mean something.

For **search**, I filter notes with JavaScript on the client side instead of hitting the server on every keystroke it just feels instant that way since the notes are already loaded.

I gave **analytics its own page** rather than cramming a chart onto the dashboard, mainly to keep the dashboard fast and simple while still giving a place to actually look at study patterns when you want to.

The **flashcard quiz** was the hardest part to get right figuring out how to store questions/answers, track a quiz attempt, and generate a result at the end took a few tries before it worked the way I wanted.

Mobile support was something I cared about from the start, not an afterthought, since this is meant to be something I'd actually open on my phone between classes.

## How to Run

1. Install dependencies:
   ```
   pip install flask flask-session werkzeug
   ```
2. Set up the database (first time only):
   ```
   python init_db.py
   ```
3. Run the app:
   ```
   flask run
   ```
4. Open the local link from the terminal, log in (or register a new account), and start using NeuraNotes.
