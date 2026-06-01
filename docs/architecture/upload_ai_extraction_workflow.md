# Upload To AI Extraction Workflow

This diagram focuses only on the upload section through OCR and AI extraction, including where files and extracted data are saved.

```mermaid
flowchart TD
    A["User submits Upload form<br/>POST /upload/documents"] --> B["main.py: upload_documents()"]

    B --> C["Normalize choices<br/>OCR: rapidocr/tesseract/mistral/auto<br/>AI: local/mistral"]
    C --> D["pipeline.py: process_uploaded_files()"]

    D --> E["Create UploadSession<br/>uploads/upload_NNNN/"]
    E --> E1["Create folders:<br/>originals/<br/>preprocessed/<br/>extracted_images/<br/>debug/<br/>ocr_texts/"]

    D --> F{"Input type"}

    F -->|Uploaded file| G["save_uploaded_file()"]
    G --> G1["Saved to:<br/>uploads/upload_NNNN/originals/{uuid}.{ext}"]
    G1 --> H["process_single_file()"]

    F -->|Pasted text| T["Direct text input"]
    T --> AI0["get_ai_extractor(local or mistral)"]
    AI0 --> AI1["extract_from_text(text_input)"]

    H --> I{"File extension"}

    I -->|Image| IMG["process_image_file()"]
    I -->|PDF| PDF["process_pdf_file()"]
    I -->|DOCX| DOCX["process_docx_file()"]

    DOCX --> DOCX1["Extract text from DOCX"]
    DOCX --> DOCX2["Extract embedded DOCX images"]
    DOCX2 --> DOCX3["Saved to:<br/>uploads/upload_NNNN/extracted_images/{docx_stem}/"]
    DOCX1 --> AI_DOCX["AI extract from direct DOCX text"]
    DOCX3 --> IMG

    PDF --> PDF1["Try PDF text layer"]
    PDF --> PDF2["Extract embedded PDF images"]
    PDF2 --> PDF3["Saved to:<br/>uploads/upload_NNNN/extracted_images/{pdf_stem}_embedded/"]
    PDF --> PDF4["If no embedded images:<br/>render pages"]
    PDF4 --> PDF5["Saved to:<br/>uploads/upload_NNNN/extracted_images/{pdf_stem}_pages/"]
    PDF1 --> AI_PDF["AI extract from direct PDF text"]
    PDF3 --> IMG
    PDF5 --> IMG

    IMG --> Q["analyse_image()"]
    Q --> P["preprocess_image()"]
    P --> P1["Debug step images saved to:<br/>uploads/upload_NNNN/debug/{image_stem}/"]
    P --> P2["Final OCR image saved to:<br/>uploads/upload_NNNN/preprocessed/{image_stem}_final.png"]

    P2 --> OCR["Selected OCR engine runs<br/>RapidOCR / Tesseract / Mistral / Auto"]
    OCR --> OCR2["Best OCR text selected by score"]
    OCR2 --> OCR3["Raw OCR text saved to:<br/>uploads/upload_NNNN/ocr_texts/{image_stem}.txt"]

    OCR2 --> CHECK{"Useful OCR text?"}
    CHECK -->|Too short / MRZ-only| SKIP["Skip AI extraction<br/>extracted_data = {}"]
    CHECK -->|Useful text| STRIP["Strip MRZ lines<br/>Detect document type"]
    STRIP --> AI2["get_ai_extractor(local or mistral)"]

    AI2 -->|local| LOCAL["LocalOllamaExtractor<br/>POST localhost:11434/api/generate<br/>model = LOCAL_TEXT_MODEL"]
    AI2 -->|mistral| MISTRAL["MistralAIExtractor<br/>POST api.mistral.ai/v1/chat/completions<br/>model = MISTRAL_EXTRACT_MODEL"]

    LOCAL --> AI3["Parse JSON response<br/>apply overrides<br/>normalize fields"]
    MISTRAL --> AI3

    AI_DOCX --> AI3
    AI_PDF --> AI3
    AI1 --> AI3
    SKIP --> R["Result object"]
    AI3 --> R

    R --> MERGE["merge_extraction_results(all_results)"]
    MERGE --> MAP["map_extracted_to_employee_fields()"]
    MAP --> SAVE["save_employee_draft()"]

    SAVE --> DB1["Saved to database:<br/>Employee row with extracted fields<br/>status = draft"]
    SAVE --> DB2["Saved to database:<br/>AuditLog action = ocr_draft_save"]

    D --> REPORT["Write session OCR report"]
    REPORT --> REPORT1["Saved to:<br/>uploads/upload_NNNN/ocr_report.txt"]

    DB1 --> RENAME["Rename upload folder after employee ID/name exists"]
    RENAME --> FINAL["Final upload folder:<br/>uploads/{first}_{last}_{employee_id}/"]
    FINAL --> EMP["employee.upload_session_dir saved in DB"]
```

## Save Points

- Original uploads: `uploads/upload_NNNN/originals/`
- Extracted PDF/DOCX images: `uploads/upload_NNNN/extracted_images/`
- Preprocessed OCR images: `uploads/upload_NNNN/preprocessed/`
- Debug preprocessing images: `uploads/upload_NNNN/debug/{image_stem}/`
- Raw OCR text per image: `uploads/upload_NNNN/ocr_texts/{image_stem}.txt`
- Combined OCR report: `uploads/upload_NNNN/ocr_report.txt`
- AI extracted fields: saved into the `Employee` database row through `save_employee_draft()`
- Upload folder final name: renamed to `uploads/{first}_{last}_{employee_id}/`
- Final folder path: saved in `employee.upload_session_dir`

Note: AI extractor output is not saved as a standalone JSON file. It is merged, mapped to employee fields, and saved into the database.
