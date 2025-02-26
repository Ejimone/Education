# Education
this is an educational project, 


Code
# Google Classroom Assignment Uploader

This project is a Flask-based web application that allows users to authenticate with Google, list their enrolled courses, view assignments for a specific course, and upload assignment submissions to Google Classroom and Google Drive.

## Overview

This application streamlines the process of uploading assignments to Google Classroom. It is designed for students as part of a project to build an AI that retrieves assignments, completes them, and submits them automatically.

## Tech Stack

- **Backend**: Python (Flask) - Handles API requests, authentication, and interactions with Google APIs.
- **Frontend**: HTML, CSS, JavaScript - Provides a user-friendly interface for course selection, assignment viewing, and file submission.
- **APIs**: Google Classroom API, Google Drive API - For retrieving assignments and uploading files.
- **Authentication**: OAuth 2.0 with JSON token storage (token.json).

## Setup Instructions

### Google Cloud Setup

1. Create a project in Google Cloud Console (https://console.cloud.google.com/).
2. Enable Google Classroom API and Google Drive API.
3. Create an OAuth 2.0 Client ID (Desktop app) and download `credentials.json`.
4. Place `credentials.json` in the project root directory.

### Install Dependencies

```bash
pip install flask google-api-python-client google-auth-oauthlib google-auth-httplib2
Usage
Run the Flask application:

bash
flask run
Open your browser and navigate to http://localhost:5000.

Endpoints
/: Renders the main page.
/auth: Initiates the OAuth flow for Google authentication.
/courses: Lists all enrolled courses.
/assignments/<course_id>: Lists assignments for a specific course.
/submit: Submits an assignment.
Logging
Logs are saved to app.log and rotated with a maximum size of 10MB and 5 backup files.

License
This project is licensed under the MIT License. See the LICENSE file for more details.
