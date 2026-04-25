# DevCareer AI

AI-powered career assistant for software developers. Built with Django and Claude AI.

## Features

- Persistent AI chat with full conversation history
- Personalized guidance based on your profile (skills, experience, job preferences)
- PDF resume upload with text extraction for AI context
- Skill gap analysis, resume feedback, interview prep, job search tips
- Markdown rendering in AI responses

## Tech Stack

- Django 5 + SQLite
- Claude claude-sonnet-4-6 (Anthropic)
- Tailwind CSS v4 (CDN)
- Font Awesome 6

## Setup

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run migrations
python3 manage.py migrate

# Start server
python3 manage.py runserver
```

Visit `http://localhost:8000`

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `DEBUG` | `True` for local dev (default) |
