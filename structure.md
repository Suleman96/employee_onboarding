C:\Users\jobs\cleaning_automation\
│
├── main.py                    ← FastAPI app — entry point, run this to start
├── config.py                  ← loads all settings from .env file
├── database.py                ← SQLite models and setup (expanded schema)
├── schemas.py                 ← Pydantic v2 validation models
├── ocr_engines.py             ← ALL OCR engines — Tesseract, EasyOCR, Google, AWS, Azure, Mistral
├── ocr_extract.py             ← OCR pipeline: raw text → Mistral AI → structured JSON
├── ordio_client.py            ← Ordio API: create, read, update, delete (CRUD)
├── alerts.py                  ← Telegram notification sender
├── .env                       ← ALL API keys and secrets (NEVER commit this)
├── requirements.txt           ← all Python packages with versions
│
├── templates/                 ← Jinja2 HTML templates
│   ├── base.html              ← shared layout (header, nav, footer)
│   ├── dashboard.html         ← main screen — pending + approved records
│   ├── upload.html            ← file upload + OCR engine selector + manual form
│   └── review.html            ← manager review, approval/rejection screen
│
├── static/                    ← CSS and JavaScript
│   ├── style.css
│   └── app.js
│
├── templates_contract/        ← Word contract templates for Project 2
│   └── AV_BEFRISTET_40Std.docx ← copy of the actual contract template
│
├── data/
│   └── employees.db           ← SQLite database (auto-created on first run)
│
├── uploads/                   ← temporarily stores uploaded ID images
│
├── contracts/                 ← generated contracts saved here (Project 2)
│   └── 2026/
│       └── 03/
│           └── Mustermann_Max_20260318.docx
│
├── logs/
│   └── app.log                ← rotating log file (auto-created)
│
└── venv/                      ← Python 3.13 virtual environment