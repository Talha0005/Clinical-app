# DigiClinic Backend

This is the Python backend for DigiClinic, implementing an MCP (Model Context Protocol) server with FastAPI.

## Prerequisites (macOS)

### 1. Install Python 3.10+

Check if Python is already installed:
```bash
python3 --version
```

**Note: This project requires Python 3.10 or later for MCP compatibility.**

If you need to install or upgrade Python, use Homebrew:
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11 (recommended)
brew install python@3.11

# You may need to create a symlink or use python3.11 explicitly
```

### 2. Verify pip is installed
```bash
pip3 --version
```

### 3. Install virtualenv (if not already available)
```bash
pip3 install virtualenv
```

## Setup Development Environment

### 1. Create Virtual Environment
```bash
cd backend
python3 -m venv .venv
```

### 2. Activate Virtual Environment
```bash
source .venv/bin/activate
```

You should see `(.venv)` at the beginning of your terminal prompt.

### 3. Upgrade pip (recommended)
```bash
pip install --upgrade pip
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

## Running the MCP Server

### 1. Make sure your virtual environment is activated
```bash
source .venv/bin/activate
```

### 2. Run the server
```bash
# Option 1: From backend directory (recommended)
python -m mcp_server.server

# Option 2: From mcp_server directory
cd mcp_server
python server.py
```

The server will start on `http://localhost:8000` with:
- SSE endpoint at `/sse`
- OAuth endpoints for Claude integration
- Patient database tools
- Medical knowledge tools (NICE CKS)

## Exposing Server with ngrok (for remote access)

To make your local MCP server accessible from the internet (useful for testing with Claude or remote clients), you can use ngrok.

### 1. Install ngrok

#### Option A: Download from ngrok website
1. Go to https://ngrok.com/download
2. Sign up for a free account
3. Download the appropriate version for your OS
4. Extract and move ngrok to your PATH

#### Option B: Install with Homebrew (macOS)
```bash
brew install ngrok/ngrok/ngrok
```

### 2. Authenticate ngrok (one-time setup)
After signing up for ngrok:
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```
(Replace `YOUR_AUTHTOKEN_HERE` with your actual authtoken from the ngrok dashboard)

### 3. Run ngrok to expose your MCP server

First, make sure your MCP server is running on localhost:8000:
```bash
# In one terminal, start the MCP server
source .venv/bin/activate
python -m mcp_server.server
```

Then in another terminal, start ngrok:
```bash
# Expose port 8000 with HTTP
ngrok http 8000
```

ngrok will display output like:
```
Session Status                online
Account                       your-email@example.com
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:8000
```

### 4. Use the public URL

Your MCP server is now accessible at the ngrok URL (e.g., `https://abc123.ngrok-free.app`). You can:
- Use this URL to connect Claude or other MCP clients
- Access the server endpoints like `https://abc123.ngrok-free.app/message`
- View the ngrok web interface at `http://127.0.0.1:4040` for request logs

### Notes:
- Free ngrok URLs change each time you restart ngrok
- The free tier has limitations on connections per minute
- For production use, consider ngrok paid plans or other tunneling solutions

## Connecting to Claude Web

Once you have your MCP server running with ngrok, you can connect it to Claude Web for interactive medical consultations.

### Prerequisites
- Claude Pro subscription (paid version - required for custom connectors)
- MCP server running locally on port 8000
- ngrok exposing the server to the internet

### Step-by-Step Connection

1. **Start your MCP server** (as described above):
   ```bash
   source .venv/bin/activate
   python -m mcp_server.server
   ```

2. **Start ngrok** (in another terminal):
   ```bash
   ngrok http 8000
   ```
   Note the forwarding URL (e.g., `https://abc123.ngrok-free.app`)

3. **Open Claude Web** and go to **Settings > Connectors**

4. **Add Custom Connector**:
   - Click "Add Custom Connector"
   - **Name**: `Digiclinic` (or any name you prefer)
   - **URL**: Take your ngrok URL and add `/sse` to the end
     - Example: `https://abc123.ngrok-free.app/sse`

5. **Test the connection**:
   - If successful, you should see the connector marked as "Connected"
   - Try asking Claude: "Can you check the patient database?"
   - Claude should be able to list patients and retrieve patient records

### Troubleshooting Connection Issues
- Ensure the MCP server is running and accessible at `http://localhost:8000`
- Verify ngrok is forwarding correctly by visiting the ngrok URL in your browser
- Make sure you're using the `/sse` endpoint in Claude Web
- Check the ngrok web interface at `http://127.0.0.1:4040` for request logs

## Setting up a Medical Consultation Project

For the best experience, create a dedicated Claude project with medical consultation context.

### Creating the Project

1. **In Claude Web**, go to **Projects** and create a new project
2. **Name**: `Digiclinic Medical Consultations` (or similar)
3. **Add the Digiclinic connector** to this project
4. **Set the project instructions** (copy the text below):

```
You are a very experienced GP and medical consultant in the UK. You are manning Digiclinic, a revolutionary digital medical clinical system. Your job is to greet patients, talk to them, ask them questions to try to diagnose if their symptoms are due to any specific medical conditions. You have access to a patient database via the connected Digiclinic tools. You can get all patient names and National Insurance numbers and then ask for the patient history by giving the tool the name and National Insurance Number.

Be caring, be inquisitive, go through a process asking questions to try to diagnose any issues, remembering that there may not actually be anything wrong.

Consider the following in your conversations: past medical/surgical history, drug history, allergies, social history, review of systems (ROS).
Use Socrates protocol for pain and integrated GAD-7/PHQ-9 scoring.

Do not engage on any other topic apart from speaking to the patient about their condition. Do not talk about anything else. Always politely ask how they are.
```

### Using the Medical Consultation System

Once set up, you can:
- Start conversations in the Digiclinic project
- Claude will act as a GP and can access patient records
- Test with questions like "I'm Sarah Johnson, I'd like to discuss my medical history"
- Claude will use the patient database to provide informed medical consultations

### Sample Test Patients

The system includes sample patients you can test with:
- **Sarah Johnson** (NI: AB123456C) - Complex medical history
- **Michael Brown** (NI: CD789012E) - Cardiovascular conditions  
- **Emma Wilson** (NI: EF345678G) - Mental health history

Try asking Claude to look up any of these patients to test the system.

## Deactivating Virtual Environment

When you're done working:
```bash
deactivate
```

## Project Structure

```
backend/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── .venv/                 # Virtual environment (hidden, ignored by git)
└── mcp_server/           # MCP server implementation
    ├── server.py         # Main FastAPI server
    ├── tools.py          # Tool implementations
    └── tools/            # Individual tool modules
        ├── patient.py    # Patient database tools
        └── nice_cks.py   # Medical knowledge tools
```

## Troubleshooting

### Python Version Issues
If you get errors about Python version requirements:
```bash
# Check your Python version
python3 --version

# If you have multiple Python versions, try using python3.11 explicitly
python3.11 -m venv .venv
source .venv/bin/activate
python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r requirements.txt
```

### MCP Package Issues
If you get errors about `mcp` package not found, make sure you're using Python 3.10+:
```bash
# Try installing the development version if needed
pip install git+https://github.com/modelcontextprotocol/python-sdk.git
```

## Development Notes

- The virtual environment (`.venv/`) is excluded from git via `.gitignore`
- Always activate the virtual environment before running the server
- Use `pip freeze > requirements.txt` to update dependencies
- The server uses JSON mocks for Phase 1 development (PostgreSQL planned for production)
- **Requires Python 3.10+ for MCP compatibility**