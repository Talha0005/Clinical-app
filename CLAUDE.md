# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DigiClinic is an AI-powered digital medical clinic prototype designed for the NHS. The system features LLM-powered medical consultants with access to comprehensive medical literature for evidence-based diagnostics and treatment recommendations.

## Key Documentation

- **README.md**: Contains project overview, target architecture (Python/React/TypeScript/PostgreSQL), development guidelines, and team standards
- **roadmap.md**: Detailed 7-phase prototype development roadmap from basic MCP server to full NHS system integration with voice and avatar capabilities

## Current Repository Structure

```
digiclinic/
├── CLAUDE.md              # This file - project guidance
├── README.md              # Project overview and guidelines  
├── roadmap.md             # 7-phase development roadmap
├── requirements.txt       # Python dependencies
├── backend/               # Python FastAPI server implementation
│   ├── main.py            # Main FastAPI application
│   ├── auth.py            # JWT authentication
│   ├── api/               # API endpoints
│   │   ├── voice.py       # Voice processing endpoints
│   │   ├── nhs_terminology_api.py # NHS terminology endpoints
│   │   └── medical_intelligence.py # Phase 2 medical AI endpoints
│   ├── services/          # Core business logic services
│   │   ├── chat_service.py        # Chat conversation management
│   │   ├── llm_router.py          # Multi-model LLM routing
│   │   ├── voice_service.py       # Voice processing with AssemblyAI
│   │   ├── clinical_agents.py     # Enhanced clinical reasoning agents
│   │   ├── nhs_terminology.py     # NHS terminology server integration
│   │   ├── vision_processing.py   # Medical image analysis
│   │   ├── medical_knowledge.py   # Evidence-based knowledge base
│   │   └── medical_observability.py # Langfuse medical compliance tracking
│   ├── medical/           # Medical data sources
│   │   ├── base.py        # Medical data interfaces
│   │   └── nice_cks.py    # NICE Clinical Knowledge Summaries
│   ├── model/             # Data models
│   │   └── patient.py     # Patient data model
│   └── dat/               # Data files
│       ├── patient-db.json    # Mock patient database
│       ├── nice-topics.json   # NICE CKS topics
│       └── prompts.json       # System prompts
└── frontend/              # React/TypeScript application
    ├── src/               # Source code
    ├── dist/              # Built application
    └── package.json       # Frontend dependencies
```

## Architecture

### Core Technology Stack
- **Backend**: Python FastAPI with multi-agent AI architecture
- **Frontend**: React.js with TypeScript, Voice Recording, Medical Image Upload
- **Authentication**: JWT-based security with role-based access
- **Database**: JSON mocks for development (PostgreSQL planned for production)
- **AI/ML**: Multi-model LLM routing (Claude Sonnet/Opus), Medical Image Analysis
- **Observability**: Langfuse for AI tracing and medical compliance monitoring

### Phase 2 Enhanced Architecture
- **Clinical Agents**: History Taking, Symptom Triage, Differential Diagnosis
- **NHS Terminology**: FHIR-compliant SNOMED CT, ICD-10, dm+d integration
- **Medical Vision**: AI-powered medical image analysis with clinical coding
- **Evidence Base**: NICE CKS integration with evidence-based recommendations
- **Voice Processing**: Real-time speech-to-text with AssemblyAI
- **Compliance**: Medical-grade observability and audit trails

## Current Implementation Status

**Phase 1**: Basic MCP Server with Claude Integration ✅ **COMPLETE**
- MCP server implemented with FastAPI
- SSE transport for Claude web interface  
- Patient database tools (JSON-based)
- Medical knowledge tools (NICE CKS integration)
- OAuth endpoints for Claude compatibility

**Phase 2**: Enhanced Medical Intelligence ✅ **COMPLETE**
- Multi-agent clinical reasoning system
- NHS Terminology Server integration (SNOMED CT, ICD-10, dm+d)
- Medical image analysis with AI vision processing
- Evidence-based medical knowledge base with NICE guidelines
- Voice processing with real-time transcription
- Medical compliance tracking and observability
- Comprehensive API endpoints for all Phase 2 services

**Configuration Status**:
- ✅ requirements.txt with all Phase 2 dependencies
- ✅ Frontend built and deployed
- ✅ Full API documentation available

## Development Commands

**Local Development:**
```bash
cd backend
source venv/bin/activate
python main.py  # Serves frontend + backend on port 8000
```

**Railway Deployment:**
This project deploys to Railway using the `Procfile` which runs `python main.py` from the project root.

**Important**: The Python virtual environment (.venv) is located in the `backend/` directory, not the project root.

## Phase 2 API Endpoints

### Core Medical Intelligence APIs
- **Clinical Agents**: `/api/medical/clinical/*` - History taking, triage, comprehensive assessment
- **NHS Terminology**: `/api/medical/terminology/*` - SNOMED CT, ICD-10, dm+d lookups and translations
- **Medical Vision**: `/api/medical/vision/*` - Medical image analysis and processing
- **Knowledge Base**: `/api/medical/knowledge/*` - Evidence-based responses and drug interactions
- **Compliance**: `/api/medical/compliance/*` - Medical observability and audit reporting

### Health Monitoring
- **System Status**: `/api/medical/system/status` - Overall Phase 2 service health
- **Service Health**: `/api/medical/health/*` - Individual service health checks

## Environment Variables for Phase 2

```bash
# Core AI
ANTHROPIC_KEY=sk-ant-...              # Required for Claude models
JWT_SECRET=your-jwt-secret            # Required for authentication

# Phase 2 Medical Intelligence
LANGFUSE_PUBLIC_KEY=pk-lf-...         # Optional: Medical observability
LANGFUSE_SECRET_KEY=sk-lf-...         # Optional: Medical observability
LANGFUSE_HOST=https://cloud.langfuse.com # Optional: Langfuse host

# Voice Processing
ASSEMBLYAI_API_KEY=your-key           # Optional: Voice transcription

# NHS Terminology Server (Optional - public endpoints available)
NHS_TERMINOLOGY_CLIENT_ID=your-id    # Optional: For authenticated access
NHS_TERMINOLOGY_CLIENT_SECRET=secret # Optional: For authenticated access
```

## Development Approach

**Phase 2 Complete**: Enhanced Medical Intelligence system with:
- Multi-agent clinical reasoning
- NHS-compliant terminology integration
- Medical image analysis capabilities  
- Evidence-based knowledge base
- Voice processing integration
- Medical compliance monitoring

Next phases focus on custom web interface, avatar integration, and extended NHS system integrations as outlined in roadmap.md.