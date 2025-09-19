# DigiClinic

DigiClinic is an AI-powered digital medical clinic prototype designed for the NHS. The system features LLM-powered medical consultants with access to comprehensive medical literature for evidence-based diagnostics and treatment recommendations.

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+** and npm
- **Python 3.11+** (for Railway deployment compatibility)
- Git

### 1. Clone Repository
```bash
git clone https://github.com/doogie-ai/digiclinic.git
cd digiclinic
```

### 2. Build Frontend
```bash
cd frontend
npm install
npm run build
```

### 3. Setup Backend
```bash
cd backend
source venv/bin/activate  # venv already exists
pip install -r requirements.txt
```

### 4. Run Server
```bash
cd backend
python main.py
```

**✅ Open:** `http://localhost:8000`

## 🚀 Railway Deployment

This project is fully configured for one-click Railway deployment with automatic GitHub integration.

### Deployment Files
- `railway.json` - Railway deployment configuration
- `requirements.txt` - Root-level Python dependencies
- `Procfile` - Process configuration (`python backend/main.py`)
- `.python-version` - Python 3.11 specification
- `frontend/dist/` - Pre-built frontend assets

### Deploy to Railway

**Option 1: GitHub Auto-Deploy (Recommended)**
1. Go to [railway.app](https://railway.app) 
2. Create new project → "Deploy from GitHub repo"
3. Select your `doogie-ai/digiclinic` repository
4. Railway automatically detects and deploys your app
5. Auto-deploys from `main` branch on every push

**Option 2: Railway CLI**
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Environment Variables

**Required Variables:**
- `ADMIN_PASSWORD` - Password for admin user login

**Optional Variables:**
- `JWT_SECRET` - JWT signing secret (has secure default)
- `PORT` - Automatically set by Railway (don't override)

#### Setting Environment Variables in Railway

**Method 1: Railway Dashboard (Recommended)**
1. Go to your Railway project dashboard
2. Click on your **digiclinic** service
3. Navigate to the **"Variables"** tab
4. Click **"New Variable"**
5. Enter variable name (e.g., `ADMIN_PASSWORD`) and value
6. Click **"Add"**
7. **⚠️ Important:** Click **"Deploy"** to apply changes

**Method 2: RAW Editor (For Multiple Variables)**
1. Go to service **Variables** tab
2. Click **"RAW Editor"**
3. Paste in `.env` format:
   ```
   ADMIN_PASSWORD=your_secure_password
   JWT_SECRET=your_jwt_secret_key
   ```
4. Click **"Deploy"** to apply changes

**Method 3: Railway CLI**
```bash
# Set variables via CLI
railway variables set ADMIN_PASSWORD=your_secure_password
railway variables set JWT_SECRET=your_jwt_secret

# View current variables
railway variables
```

**⚠️ Security Notes:**
- Use strong passwords for `ADMIN_PASSWORD`
- Consider using Railway's "Sealed Variables" for sensitive data
- Environment variables are available during build and runtime

### Post-Deployment
- Your app will be available at the Railway-provided URL
- Frontend served at root (`/`)
- API endpoints at `/api/*`
- Automatic HTTPS and custom domain support available

## 🛠 Development Commands

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Development mode (separate dev server)
npm run dev

# Lint code
npm run lint
```

### Backend Development
```bash
cd backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run simple frontend server
python main.py

# Run full MCP server (later)
python mcp_server/server.py

# Run tests
pytest tests/
```

## 📁 Project Structure

```
digiclinic/
├── railway.json           # Railway deployment config
├── requirements.txt       # Python dependencies (root level)
├── Procfile              # Process configuration
├── .python-version       # Python version specification
├── frontend/              # React + TypeScript frontend
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── pages/         # Page components
│   │   └── lib/           # Utilities
│   ├── package.json
│   └── dist/              # Build output (served by backend)
├── backend/               # Python backend
│   ├── main.py           # FastAPI server (serves frontend + API)
│   ├── mcp_server/       # MCP server implementation
│   ├── requirements.txt  # Backend-specific dependencies
│   └── venv/             # Virtual environment (local dev)
└── docs/                 # Project documentation
```

## 🔧 Current Features

### ✅ Frontend
- Modern React 18 + TypeScript
- NHS-styled medical UI with shadcn/ui
- Chat interface for medical consultations
- Responsive design
- Production build system

### ✅ Backend
- FastAPI server serving React frontend + API endpoints
- JWT authentication system
- MCP (Model Context Protocol) integration
- Patient database tools (JSON-based mock data)
- Medical knowledge integration (NICE CKS scraping)
- Comprehensive test suite with pytest
- Railway deployment ready

## 📋 Roadmap

See [roadmap.md](./roadmap.md) for the complete 7-phase development plan from basic functionality to full NHS integration.

## 🧪 Testing

```bash
# Frontend
cd frontend
npm run lint

# Backend
cd backend
source venv/bin/activate
pytest tests/
```

## 🔒 Security Note

**⚕️ This is a prototype system for research and development. Not approved for clinical use.**

## 📞 Support

For issues or questions, please open an issue on GitHub.