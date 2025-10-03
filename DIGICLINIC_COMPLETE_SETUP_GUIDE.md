# 🏥 DigiClinic - Complete Setup & Run Guide

This is your **ONE-SPOT** guide for everything about running the DigiClinic AI-powered medical clinic prototype. Everything you need to know is here!

## 🎯 What is DigiClinic?

DigiClinic is an **AI-powered digital medical clinic prototype** designed for NHS integration. It features:
- **LLM-powered medical consultants** (Claude, GPT, Gemini)
- **Comprehensive medical literature** integration
- **Evidence-based diagnostics** and treatment recommendations
- **Patient database** with FHIR compliance
- **Synthetic medical data generation** using Synthea
- **Real NHS terminology** integration

---

## 🔧 Prerequisites & Requirements

### System Requirements
| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.10+ | Backend API server |
| **Node.js** | 18+ | Frontend React app |
| **Java** | 8+ | Synthea data generation |
| **Git** | Latest | Version control |
| **XAMP** for window | / | for linux **WAMP** |
| **Java**|

### Quick Version Check
```bash
python --version    # Should show 3.10+
java -version       # Should show Java 8+
node --version      # Should show 18+
npm --version       # Package manager
```

---

## 📁 Project Structure

```
digiclinic-main 10/
├── backend/                    # Python FastAPI server
│   ├── main.py                # 🚀 MAIN SERVER FILE
│   ├── api/                   # API endpoints
│   ├── models/                # Database models
│   ├── services/              # Business logic
│   ├── llm/                   # AI model integration
│   ├── config/                # Configuration
│   └── venv/                  # Virtual environment
├── frontend/                  # React TypeScript app
│   ├── src/                   # Source code
│   ├── package.json           # Dependencies
│   └── dist/                  # Build output
├── data/                      # Medical data storage
└── synthea/                   # Synthetic data generator
```

---

## 🚀 INSTALLATION METHODS

### Method 1: Automated Setup (Easiest - Recommended)

```bash
# Navigate to the project
cd "digiclinic-main 10/digiclinic-main 10"

# Run the automated setup (Windows)
SETUP_ONCE.bat

# Or run manually:
START_DIGICLINIC.bat
```

### Method 2: Manual Setup (Step by Step)

#### Step 1: Backend Setup
```bash
# Navigate to backend
cd "digiclinic-main 10/digiclinic-main 10/backend"

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
copy env.example .env
# Edit .env with your API keys (see Configuration section)
```

#### Step 2: Frontend Setup
```bash
# Navigate to frontend
cd "digiclinic-main 10/digiclinic-main 10/frontend"

# Install Node.js dependencies
npm install

# Build frontend (optional - dev mode auto-builds)
npm run build
```

### Method 3: One-Line Setup (PowerShell)
```powershell
cd "digiclinic-main 10/digiclinic-main 10"; .\SETUP_ONCE.bat
```

---

## ⚙️ Configuration (.env File)

Create `.env` file in `backend/` directory:

```bash
# REQUIRED API KEYS - Get from these services:
ANTHROPIC_KEY=sk-ant-api03-your_claude_key_here
OPENAI_API_KEY=sk-your_openai_key_here  
GOOGLE_API_KEY=your_gemini_key_here

# DATABASE CONFIGURATION
DATABASE_URL=sqlite:///dat/digiclinic.db
# OR for MySQL:
# DATABASE_URL=mysql+pymysql://root:@localhost:3306/digiclinic

# SECURITY
SECRET_KEY=your_jwt_secret_key_here

# OPTIONAL SETTINGS
DEBUG=true
REQUIRE_VERIFICATION=0
SQL_ECHO=false
```

### 🔑 Getting API Keys

| Service | Where to Get | Cost |
|---------|-------------|------|
| **Claude (Anthropic)** | https://console.anthropic.com/ | Free tier available |
| **OpenAI GPT** | https://platform.openai.com/api-keys | Pay per use |
| **Google Gemini** | https://aistudio.google.com/app/apikey | Free tier available |

---

## 🏃‍♂️ How to RUN the Project

### Method 1: Single Command (Windows)
```bash
# Double-click or run:
RUN_DIGICLINIC.bat
```

### Method 2: Manual Start
```bash
# Terminal 1 - Backend Server
cd "digiclinic-main 10/digiclinic-main 10/backend"
python main.py

# Terminal 2 - Frontend Server  
cd "digiclinic-main 10/digiclinic-main 10/frontend"
npm run dev
```

### Method 3: Using PowerShell Scripts
```powershell
# For Windows PowerShell:
.\SETUP_ONCE.bat    或者  .\START_DIGICLINIC.bat
```

---

## 🌐 Access URLs

Once running, access the application at:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | Main web interface |
| **Backend API** | http://localhost:8000 | API server |
| **API Docs** | http://localhost:8000/docs | Swagger documentation |
| **Health Check** | http://localhost:8000/health | Server status |

---

## 📊 Key Features & Testing

### 1. User Authentication
```bash
# Test user credentials:
Username: 476172
Password: (set during setup)
```

### 2. AI Chat Interface
- **Claude**: Most sophisticated reasoning
- **GPT-4**: Good general knowledge  
- **Gemini**: Fast responses

### 3. Admin Features
```bash
# Admin access:
1. Login with admin credentials
2. Click Database icon → Data Generation
3. Generate synthetic medical data
4. View patient chat history
```

### 4. Data Generation (Synthea)
```bash
# Features:
✅ Automated patient data generation
✅ FHIR validation  
✅ NHS terminology integration
✅ ML model training pipeline
```

---

## 🔍 Important API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `POST /api/auth/logout` - User logout

### Chat Management
- `GET /api/chat/my-history` - User chat history
- `POST /api/chat/send-message` - Send message to AI
- `DELETE /api/chat/conversation/{id}` - Delete conversation

### Admin Functions
- `GET /api/admin/patient-history/{username}` - Get patient history
- `DELETE /api/admin/conversation/{id}` - Delete conversation
- `DELETE /api/admin/user/{username}` - Delete user

### Data Generation (Admin Only)
- `POST /api/synthea-validation/generate-and-validate` - Generate & validate
- `POST /api/synthea/generate` - Generate patient data
- `POST /api/synthea/generate/cohort` - Generate specific cohort

---

## 🛠 Development Commands

### Frontend Development
```bash
cd frontend

# Development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Preview production build
npm run preview
```

### Backend Development
```bash
cd backend

# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run server
python main.py

# Run with debugging
python -c "import uvicorn; uvicorn.run('main:app', reload=True)"

# Run tests
pytest tests/

# Database migration
python -c "from config.database import init_db; init_db()"
```

---

## ❌ Common Issues & Solutions

### Issue 1: Java Not Found
```bash
ERROR: Java runtime is required to generate synthetic data
```
**Solution**: Install Java 8+ from https://adoptium.net/

### Issue 2: Port Already in Use
```bash
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```
**Solution**: 
```bash
# Kill process on port 8000 (Windows)
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Change port in main.py if needed
```

### Issue 3: Import Errors
```bash
ImportError: No module named 'fhir.resources'
```
**Solution**: 
```bash
cd backend
pip install -r requirements.txt
```

### Issue 4: Frontend Build Errors
```bash
ERROR: Unexpected "{"
```
**Solution**: 
```bash
cd frontend
npm install
npm run build  # Check for errors
```

### Issue 5: Database Connection Issues
```bash
# For SQLite (default):
# Check if dat/digiclinic.db exists

# For MySQL:
# Ensure MySQL server is running
# Check connection string in .env
```

---

## 🧪 Testing Commands

### Frontend Testing
```bash
cd frontend
npm run lint              # Check code quality
npm run build             # Test production build
npm run preview           # Test production build locally
```

### Backend Testing
```bash
cd backend
pytest tests/             # Run all tests
pytest tests/test_auth.py # Test authentication
python -m pytest -v      # Verbose test output
```

### System Integration Testing
```bash
# Test complete system
python check_backend_db.py
python test_complete_system.py
python test_auth_complete.py
```

---

## 🚀 Deployment Options

### Railway Deployment (Cloud)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Local Production Build
```bash
# Build frontend
cd frontend && npm run build

# Run production server
cd backend && python main.py
```

---

## 🔊 Voice & Audio Features

The system includes voice processing capabilities:

```bash
# Voice test file location:
test_tone.wav
aa_test_local.wav

# Voice processing endpoint:
POST /api/voice/process
```

---

## 📈 Monitoring & Logs

### View Logs
```bash
# Backend logs (printed to console)
python main.py

# Check database status
python backend/check_backend_db.py

# Check MySQL users
python backend/check_mysql_users.py
```

### Health Monitoring
```bash
# Health check
curl http://localhost:8000/health

# Database status
curl http://localhost:8000/health/db
```

---

## 🎯 Quick Verification Checklist

After setup, verify everything works:

- [ ] ✅ Python 3.10+ installed
- [ ] ✅ Node.js 18+ installed  
- [ ] ✅ Java 8+ installed
- [ ] ✅ API keys in .env file
- [ ] ✅ Dependencies installed (`pip install -r requirements.txt`)
- [ ] ✅ Frontend dependencies (`npm install`)
- [ ] ✅ Backend starts: `python main.py` → http://localhost:8000
- [ ] ✅ Frontend starts: `npm run dev` → http://localhost:5173
- [ ] ✅ Login works with test user (476172)
- [ ] ✅ Chat interface responds to AI models
- [ ] ✅ Admin features accessible

---

## 📞 Support & Troubleshooting

### If Something Doesn't Work:

1. **Check Prerequisites**: Ensure Python 3.10+, Node.js 18+, Java 8+ are installed
2. **Check API Keys**: Verify .env file has correct API keys
3. **Check Dependencies**: Run `pip install -r requirements.txt` and `npm install`
4. **Check Ports**: Ensure 8000 and 5173 are available
5. **Check Logs**: Look at console output for error messages
6. **Restart**: Try restarting both servers

### Debug Commands:
```bash
# Check Python version
python --version

# Check Node version  
node --version

# Check Java version
java -version

# Check if ports are in use
netstat -an | findstr :8000
netstat -an | findstr :5173

# Test database connection
python backend/test_db_connection.py
```

---

## 🎉 Success Indicators

When everything is working correctly, you should see:

✅ **Backend Console**: `Uvicorn running on http://0.0.0.0:8000`  
✅ **Frontend Console**: `Local: http://localhost:5173`  
✅ **Browser**: DigiClinic interface loads at http://localhost:5173  
✅ **Login**: Test user (476172) can login  
✅ **Chat**: AI models respond to messages  
✅ **API Docs**: Available at http://localhost:8000/docs  

---

## 📝 Final Notes

- **This is a prototype** - Not approved for clinical use
- **API keys required** - Get free tier accounts for testing
- **Database**: Starts with SQLite, can upgrade to MySQL
- **Security**: Uses JWT authentication
- **Synthea**: Generates realistic FHIR-compliant medical data

**🚀 Happy coding! The DigiClinic AI medical platform is ready to help with medical intelligence!**

---

## 🎯 TL;DR - Quick Start

```bash
# ONE COMMAND RUN (Windows):
cd "digiclinic-main 10/digiclinic-main 10"
SETUP_ONCE.bat

# THEN RUN:
RUN_DIGICLINIC.bat

# Access: http://localhost:5173
# Test user: 476172
```

**That's it! 🎊**
