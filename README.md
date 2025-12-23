# Enrich Media

Multi-agent system to transform Facebook content into encyclopedic articles.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- Supabase account
- Gemini API key

---

## Supabase Setup

1. Create a new project at https://supabase.com
2. Navigate to SQL Editor
3. Execute the following SQL:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    summary TEXT,
    body TEXT NOT NULL,
    language VARCHAR(10) NOT NULL,
    dialect VARCHAR(50),
    source_url TEXT NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    tags TEXT[],
    categories TEXT[],
    qa_readability FLOAT,
    qa_coherence FLOAT,
    qa_redundancy FLOAT,
    qa_neutrality FLOAT,
    qa_human_likeness FLOAT,
    qa_passed BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

4. Copy URL and anon key from Settings > API

---

## Backend Setup

```powershell
cd d:\Projects\EnrichMedia\backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt

# Install spaCy model
python -m spacy download en_core_web_sm

# Install Playwright browsers
playwright install chromium

# Create .env from example
copy .env.example .env
# Edit .env with your actual values
```

---

## Frontend Setup

```powershell
cd d:\Projects\EnrichMedia\frontend

# Install dependencies
npm install

# Create .env from example
copy .env.example .env
```

---

## Run Backend

```powershell
cd d:\Projects\EnrichMedia\backend
.\venv\Scripts\Activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: http://localhost:8000

API docs at: http://localhost:8000/docs

---

## Run Frontend

```powershell
cd d:\Projects\EnrichMedia\frontend
npm run dev
```

Frontend runs at: http://localhost:5173

---

## Verification Checklist

1. Backend health check:
   - Open http://localhost:8000/health
   - Confirm: `{"status":"healthy","version":"1.0.0"}`

2. API documentation:
   - Open http://localhost:8000/docs
   - Confirm Swagger UI loads

3. Frontend loads:
   - Open http://localhost:5173
   - Confirm dark-themed homepage with URL input form

4. Database connection:
   - Check Supabase dashboard
   - Confirm `articles` table exists

5. End-to-end test:
   - Enter a public Facebook page URL
   - Click "Generate Article"
   - Wait for processing to complete
   - Confirm article appears in listing
   - Click article to view detail page

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /api/process/ | Process Facebook URL (sync) |
| POST | /api/process/async | Process Facebook URL (async) |
| GET | /api/process/status/{id} | Get async task status |
| GET | /api/articles/ | List articles |
| GET | /api/articles/{id} | Get article by ID |
| DELETE | /api/articles/{id} | Delete article |
| GET | /api/articles/search/ | Search articles |
