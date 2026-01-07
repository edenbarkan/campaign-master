# Campaign Master

A monorepo for the Campaign Master application.

## Structure

```
campaign-master/
├── backend/      # Backend services
├── frontend/     # Frontend application
└── infra/        # Infrastructure as code
```

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 18+
- Docker and Docker Compose (for containerized setup)

### Backend Setup

#### Local Development

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment file:
```bash
cp .env.example .env
```

5. Update `.env` with your database URL if needed.

6. Initialize and run migrations:
```bash
flask db init  # First time only
flask db migrate -m "Initial migration"
flask db upgrade
```

7. Run the application:
```bash
python run.py
```

The API will be available at `http://localhost:5000`

#### Docker Setup

1. Navigate to infra directory:
```bash
cd infra
```

2. Start services:
```bash
docker-compose up -d
```

3. Run database migrations:
```bash
docker-compose exec backend flask db init  # First time only
docker-compose exec backend flask db migrate -m "Initial migration"
docker-compose exec backend flask db upgrade
```

The backend will be available at `http://localhost:5000`

### API Endpoints

- `GET /healthz` - Health check endpoint
- `GET /readyz` - Readiness check endpoint (verifies database connection)

### Frontend

```bash
cd frontend
# Follow frontend-specific setup instructions
```

## Development

Each service can be run independently from its respective directory. See individual service READMEs for detailed setup instructions.
