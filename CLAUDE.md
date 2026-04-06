# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
SeeWorldWeb - Full-stack web application.

## Commands
- **Install frontend dependencies**: `cd frontend && npm install`
- **Install backend dependencies**: `cd backend && pip install -r requirements.txt`
- **Development frontend**: `cd frontend && npm run dev` (start Vite dev server)
- **Development backend**: `cd backend && uvicorn main:app --reload --port 8000` (start FastAPI dev server)
- **Build frontend**: `cd frontend && npm run build`
- **Start production frontend**: `cd frontend && npm run preview`
- **Start production backend**: `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`
- **Lint**: `cd frontend && npm run lint` (run ESLint on frontend)

## Project Structure
```
├── backend/          # Python FastAPI backend
├── frontend/         # Vue 3 frontend web application
```

## Architecture Guidelines
- Backend: Python FastAPI with WebSocket support
- Frontend: Vue 3 single-page application
- Shared TypeScript types are in `frontend/shared/`
- Backend uses Pydantic models for type safety
- Environment variables: `.env` in backend (not committed), `.env.example` for reference

## log
/logs/log_full.log