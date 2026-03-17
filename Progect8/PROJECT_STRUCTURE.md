# Project Structure

## Overview
This project has been reorganized for better maintainability. The main application code is now located in the `backend/` directory.

## Directory Structure
```
project/
├── backend/           # Main application code
│   ├── __init__.py
│   ├── app.py         # Flask app configuration and route registration
│   ├── auth.py        # Authentication routes
│   ├── tournaments.py # Tournament-related routes
│   ├── teams.py       # Team management routes
│   ├── submissions.py # Submission handling routes
│   ├── admin.py       # Admin panel routes
│   ├── app_helpers.py # Helper functions and decorators
│   ├── models.py      # Database models
│   ├── utils.py       # Utility functions
│   └── translations.py # Translation support
├── templates/         # Jinja2 templates (configured in app.py)
├── tests/            # Test files
├── run.py            # Application entry point
└── ...               # Other project files
```

## Configuration Notes
- **Templates**: Located in `templates/` directory, configured via `app.template_folder` in `backend/app.py`
- **Database**: SQLite database `data.db` in project root
- **Static files**: Not currently used

## Running the Application
To run the application, use:
```bash
python run.py
```

## Development
- All backend code is in the `backend/` package
- Tests import from `backend.models` etc.
- The application uses relative imports within the backend package