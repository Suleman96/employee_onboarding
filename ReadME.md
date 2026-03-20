# Employee Onboarding System

A backend-driven employee onboarding platform for document intake, data extraction, validation, and workflow preparation.

## Overview

This project is an early-stage employee onboarding system designed to simplify how employee information is collected, reviewed, and prepared for further HR processing.

The goal is to reduce repetitive manual work during onboarding by creating a structured workflow for:

- uploading employee-related documents
- extracting important information from those documents
- reviewing and correcting extracted data
- storing employee records in a structured database
- preparing the foundation for later contract and HR system integration

At this stage, the project is focused on building a clean and extensible base architecture rather than implementing every advanced feature immediately.

## Why this project matters

In many companies, onboarding is still heavily manual. HR or operations teams often need to read documents one by one, copy information into internal systems, and prepare contracts or records manually.

This project is being built to improve that process by combining backend engineering, document handling, structured data storage, and AI-assisted extraction into one practical workflow.

The system is intended to help with:

- reducing manual data entry
- improving consistency in employee records
- minimizing onboarding delays
- creating a scalable base for future automation

## Current goal

The current focus is to build a strong project foundation first.

That includes:

- setting up the FastAPI application properly
- organizing the project structure clearly
- creating the database layer
- defining employee-related models and schemas
- preparing the system for document-processing workflows
- making the project understandable and maintainable from the beginning

This makes the project realistic, clean, and easier to scale later.

## Planned workflow

The onboarding flow is planned to look like this:

1. A manager uploads one or more employee documents.
2. The system identifies the appropriate processing path.
3. Text is extracted from the uploaded file using document parsing and/or OCR.
4. Relevant employee fields are structured from the extracted content.
5. A manager reviews and corrects the extracted information.
6. The reviewed employee data is stored in the database.
7. Later phases can support contract preparation and external HR system integration.

## Tech stack

This project is being built with a practical stack that is highly relevant for modern backend, automation, and AI-enabled business applications.

### Backend
- **Python 3.13**
- **FastAPI**
- **Uvicorn**
- **Pydantic**

### Database
- **SQLite** for local development
- **SQLAlchemy** for ORM and database models

### Document processing
- **python-docx** for Word document handling
- **docxtpl** for future template-based contract generation
- **PDF/text extraction tools** for document reading
- **OCR pipeline** for scanned or image-based files

### Frontend
- **Jinja2 templates**
- **HTML**
- **CSS**
- **JavaScript**

### AI / automation direction
- **LLM-assisted information extraction**
- **document routing based on input type**
- **structured data validation and review workflows**

## Project structure

A simple project structure at this stage may look like this:

```text
employee_onboarding/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── routers/
├── templates/
├── static/
├── data/
└── README.md