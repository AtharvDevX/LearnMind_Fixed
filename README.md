# LearnMind — Smart Learning Companion

LearnMind is a Flask + SQLite student learning platform. The original concept and violet learning-focused interface are retained, with working account management, subjects, practice quizzes, performance tracking, resources, settings and a Gemini-powered study assistant.

## Features

- Student registration and login with securely hashed passwords.
- Personal dashboard with database-backed subject and quiz statistics.
- My Learning: add subjects, rename them, update progress and remove subjects.
- Study Debugger: five-question quizzes for Natural Language Processing, Digital Image Processing, Neural Networks and Quantitative Techniques. Add “Python Programming” to My Learning to enable its optional quiz. The answer key stays on the server; results are saved automatically.
- Progress: subject progress, quiz averages, best scores and recent attempts.
- Resources: curated links to official documentation and learning resources.
- Settings: update display name and change password.
- AI Assistant: Gemini responses, saved chat history and a clear-conversation action.
- Existing SQLite accounts and subjects are upgraded in place. Existing plain-text passwords are converted to password hashes automatically during startup.

## Requirements

- Windows 10/11, macOS or Linux
- Python 3.10 or later
- A Gemini API key for the AI Assistant (other application features work without it)

## Run on Windows (VS Code)

1. Extract this folder and open it in VS Code.
2. Open **Terminal → New Terminal** in the project directory.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

5. Create your environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

6. Open `.env` and set a newly generated Gemini API key and a long random Flask secret:

   ```env
   FLASK_SECRET_KEY=put-a-long-random-value-here
   GEMINI_API_KEY=put-your-new-gemini-key-here
   GEMINI_MODEL=gemini-3.8-flash
   FLASK_DEBUG=1
   COOKIE_SECURE=0
   ```

7. Start the app:

   ```powershell
   python app.py
   ```

8. Open **http://127.0.0.1:5000**.

You can alternatively run `start_windows.bat`; it creates the virtual environment if missing, installs requirements and starts the app.

## IMPORTANT: Updating an existing LearnMind folder

1. Stop the current Flask server with `Ctrl + C`.
2. Make a backup copy of your existing `database.db` and `.env`.
3. Replace `app.py`, the `templates` folder and the `static` folder with the files from this package.
4. Keep your existing `database.db` file in the project folder. **Do not delete it or replace it with an empty one.** The upgraded app adds the new quiz/chat tables and preserves existing accounts and subjects. It also hashes legacy plain-text passwords automatically.
5. Keep your `.env`, but replace any API key that has been exposed in screenshots, chats or source control. Create a fresh key in Google AI Studio.
6. Activate your virtual environment, install `requirements.txt`, and run `python app.py`.

This release intentionally does not include a database file or `.env` because those files contain private user records and API credentials. A new, empty database is created automatically when the app starts for the first time. When upgrading, retain your own existing database to preserve its data.

## Gemini configuration

The AI Assistant needs `GEMINI_API_KEY`. The model can be changed with `GEMINI_MODEL` in `.env` if a different model is enabled for your Google AI Studio project. If the key is not configured, all non-AI features continue to work and the chat page explains the missing configuration.

## Database and privacy

- The database file is local: `database.db` in this folder by default.
- Set `LEARNMIND_DATABASE` to use a different SQLite path.
- Passwords are stored as Werkzeug password hashes, not plain text.
- Each user's subjects, quiz history and chat history are scoped to that user's account.
- `.env`, `database.db` and `venv/` are excluded from Git via `.gitignore`.

## Notes

- Quiz scores update the progress value for a matching subject. You can also edit subject progress manually in **My Learning**.
- The built-in quiz bank covers the four original core subjects. Custom subjects can still be created and tracked; use the AI Assistant to study a custom topic.
- External learning resources require an internet connection.
- For deployment, turn off Flask debug mode, set `COOKIE_SECURE=1` behind HTTPS, use a strong secret key and configure an appropriate production WSGI server.
