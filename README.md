# SEO Analyzer AI

A comprehensive system for website SEO analysis, leveraging artificial intelligence to generate optimization suggestions.

## 🚀 Features

### 1. Technical SEO Analysis
- **Core Web Vitals**
  - Largest Contentful Paint (LCP)
  - First Input Delay (FID)
  - Cumulative Layout Shift (CLS)
- **Schema.org Analysis**
  - Validation of structured data tags
  - Implementation checks
  - Extension recommendations
- **Website Performance**
  - Lighthouse audits
  - Resource optimization
  - Load time analysis

### 2. Content Analysis
- **Content Quality**
  - Keyword analysis
  - Keyword density
  - Content uniqueness
- **Document Structure**
  - Header hierarchy (H1-H6)
  - Text length analysis
  - Readability checks
- **Meta Optimization**
  - Title tags
  - Meta descriptions
  - Open Graph tags
  - Canonical URLs

### 3. Reporting and Monitoring
- **Scoring System**
  - Overall score (0-100)
  - Element-specific scoring
  - Trends and historical comparisons
- **AI Suggestions**
  - Personalized recommendations
  - Action prioritization
  - Implementation examples
- **Data Export**
  - PDF format
  - Excel reports
  - JSON/CSV export

### 4. System Integrations
- **OpenAI**
  - Optimization suggestions
  - Semantic content analysis
  - Improvement proposals
- **Elasticsearch**
  - Report indexing
  - Fast search
  - Historical analysis
- **Lighthouse**
  - Performance audits
  - Accessibility reports
  - Best practices

### 5. Management and Security
- **User System**
  - Roles and permissions
  - Access management
  - Activity history
- **System Monitoring**
  - Performance tracking
  - Alerts and notifications
  - Rate limiting

## 🛠 Technologies

- Python 3.9+
- FastAPI
- Celery
- Redis
- Elasticsearch
- OpenAI API

## 📋 Requirements

- Python 3.9 or newer
- Redis
- Elasticsearch
- OpenAI API key

## 🔧 Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd seo
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables in the `.env` file:
```
OPENAI_API_KEY=your-api-key
ELASTICSEARCH_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379
```

## 🚦 Running the System

1. Start Redis and Elasticsearch.

2. Launch the Celery worker:
```bash
celery -A workers.celery worker --loglevel=info
```

3. Start the application:
```bash
uvicorn app.main:app --reload
```

## 📊 Performance Metrics

- Report generation time: < 5 minutes
- AI suggestion accuracy: > 90%
- System availability: > 99.9%

## 🗂 Project Structure

```
app/
├── api/endpoints/       # API endpoints
├── services/            # Business logic
├── tasks/               # Asynchronous tasks
├── core/                # Configuration and core components
└── models/              # Data models

integrations/            # External integrations
└── elasticsearch/
└── openai/
└── lighthouse/

workers/                 # Celery configuration and tasks
```

## 👥 Authors
- Marcin Plaza - Lead Developer
