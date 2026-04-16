# RahatPay - AI-Powered Parametric Income Insurance Platform

## Project Overview

RahatPay is an AI-powered parametric income insurance platform for food delivery workers (Zomato, Swiggy) in India. It provides automated payouts triggered by external events like severe weather, air pollution, or civic disruptions — without requiring riders to file a claim.

## Architecture

The project is organized into five functional modules plus an admin dashboard:

- **`Admin Dashboard Ui/`** — React 19 + Vite + Tailwind CSS v4 web interface for insurers/admins
- **`module1-registration/`** — FastAPI backend for rider identity, registration, and policy lifecycle (PostgreSQL)
- **`module2-risk-engine/`** — FastAPI AI/ML service for zone-based risk scoring and dynamic premiums (XGBoost)
- **`module3-triggers-claims/`** — FastAPI rule-based engine for monitoring triggers (weather/AQI) and claim eligibility
- **`module4-mobile-app/`** — React Native/Expo mobile app for delivery riders
- **`module5-integration/`** — End-to-end integration tests, Postman collections, and demo scripts

## Tech Stack

- **Frontend (Admin Dashboard):** React 19, Vite 8, Tailwind CSS v4, Framer Motion, Recharts, Lucide React, React Router v7
- **Mobile (Rider App):** React Native, Expo v54, Firebase (Auth & Cloud Messaging), React Navigation
- **Backend (Microservices):** Python 3.12, FastAPI, Uvicorn, SQLAlchemy (Async), Alembic, PostgreSQL
- **AI/ML:** XGBoost, Scikit-learn, Pandas, NumPy, Joblib
- **Auth:** Firebase Admin SDK
- **External APIs:** IMD (weather), OpenWeatherMap, CPCB (air quality), Razorpay (payments)

## Development Setup

### Frontend (Admin Dashboard)
- Package manager: npm
- Run: `cd 'Admin Dashboard Ui' && npm run dev`
- Port: 5000
- Host: 0.0.0.0 (configured in vite.config.js)
- All hosts allowed for Replit proxy compatibility

### Backend Modules (not running in Replit — require PostgreSQL and external services)
- Each module has its own `requirements.txt` and FastAPI app
- Originally intended to run via Docker Compose

## Workflows

- **Start application** — Runs the Admin Dashboard UI on port 5000 (webview)

## Deployment

- Type: Static site
- Build command: `cd 'Admin Dashboard Ui' && npm run build`
- Public directory: `Admin Dashboard Ui/dist`
