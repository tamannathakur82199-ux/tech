# CampusPulse — Smart Campus Complaint & Suggestion Platform

A Flask + SQLite web application for verified campus users to submit complaints/suggestions. It includes automatic text classification, duplicate/related complaint detection, urgency scoring, complaint tracking, user approval and an admin analytics dashboard.

## Technology
- Python + Flask
- SQLite database
- Scikit-learn TF-IDF + Logistic Regression for category prediction
- TF-IDF + cosine similarity for related/duplicate grouping
- HTML, CSS, JavaScript and Chart.js

## Features
1. Verified access: users register as student/faculty/staff and wait for admin approval.
2. Intelligent classification: predicts Infrastructure, Academics, Hostel, Transport, Cleanliness, IT Services, Safety & Security or Other.
3. Duplicate grouping: compares new complaint text against earlier complaints. Similarity >= 0.48 is flagged for admin review.
4. Priority detection: urgent safety/emergency terms are flagged Urgent; other operational terms can be High; remaining reports are Medium.
5. Admin dashboard: summary cards, category chart, priority chart, complaint queue, status updates, admin notes and user verification.
6. User dashboard: submit and track complaints and view admin updates.

## Run on Windows (VS Code)

1. Install Python 3.10 or newer.
2. Extract the ZIP and open the `CampusPulse` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

5. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run this once in that terminal:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

6. Install packages:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. Start the app:

   ```powershell
   python app.py
   ```

8. Open `http://127.0.0.1:5000` in your browser.

The SQLite database (`campuspulse.db`) is created automatically on first run.

## Demo administrator
- Email: `admin@campuspulse.local`
- Password: `Admin@123`

Log in as admin, open the Admin Dashboard and approve newly registered users under **User Verification**. Then log out and sign in using the approved user account.

**Security:** Change the demo password and `SECRET_KEY` before deploying publicly. Do not expose the demo admin account on a public server. For a real college deployment, connect the registration process to official college email verification or an administrator-maintained student/staff roster.

## How to test the AI features
Register and approve a test account. Submit examples such as:
- "The ceiling fan in room 204 is not working and students are uncomfortable." → likely Infrastructure / High
- "There is smoke and sparking from an exposed electrical wire near the laboratory." → Safety & Security / Urgent
- "Campus Wi-Fi is not working in the library." → likely IT Services
- Submit a second complaint with similar wording to the first → it should be flagged as related if the similarity score crosses the threshold.

The classifier is trained on a small built-in demonstration dataset. For a college project submission, expand the labelled dataset with representative campus complaints and evaluate accuracy, precision, recall and F1-score on a held-out test set. The urgency detector is a transparent keyword-based baseline, not a substitute for emergency services or human review.

## Database tables
- `users`: identity, role, password hash and verification status.
- `complaints`: complaint text, predicted category, priority, status, duplicate link, similarity score and admin notes.

## Important project limitations / next improvements
- No real email OTP is configured. Verification is administrator approval in this version.
- The included ML training examples are a starter dataset, not a validated production model.
- Duplicate detection flags likely matches for admin review; it does not automatically merge or delete reports.
- For production: add CSRF protection, rate limiting, audit logs, backups, secure deployment settings, official college identity verification and a larger labelled dataset.
