<div align="center">
  <h1>🅿️ ParkEase</h1>
  <p><strong>Parking & Fuel Station Management System</strong></p>
  <p>Bangladesh — All 8 Divisions</p>
  <br>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-0.140-green?logo=fastapi" alt="FastAPI">
    <img src="https://img.shields.io/badge/Leaflet-1.9-brightgreen?logo=leaflet" alt="Leaflet">
    <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite" alt="SQLite">
  </p>
</div>

---

## 📋 Overview

ParkEase is a web-based platform connecting drivers with parking lots and fuel stations across all 8 divisions of Bangladesh. Built as a university project with **three user roles** — Driver, Operator, and Admin.

### Features by Role

| Role | Capabilities |
|------|-------------|
| **Driver** | Find nearby parking & fuel stations on an interactive map, filter by vehicle type / fuel type / radius, reserve parking with instant digital token, view booking history with expiry alerts, get Google Maps directions |
| **Operator** | CRUD for stations, manual slot adjustment (+/-), open/close toggle, fuel price management, token lookup & booking completion |
| **Admin** | Pending approvals panel, user management (search/edit/delete), master station CRUD, analytics dashboard with revenue stats |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher ([download](https://python.org/downloads))
- Internet connection (for map tiles via CDN)

### Run (one double-click)

```powershell
# Just double-click this file:
start.bat
```

That's it. The script installs dependencies, seeds the database with 18 demo stations across Bangladesh, and opens your browser.

### Run manually

```powershell
cd backend
pip install -r requirements.txt
python seed.py
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000**

### Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@parking.com | admin123 |
| Driver | driver@test.com | pass123 |
| Operator | operator@test.com | pass123 |

---

## 🗺️ Screenshots

### Driver Map View
Interactive map with color-coded markers (blue = parking, orange = fuel), radius filters, location search, and station details in popups.

### Reservation Flow
Select station → pick time & duration → choose payment method (bKash/Nagad/Cash) → get unique 6-char token → slot auto-decrements.

### Operator Dashboard
Manage stations, adjust slot counts in real-time, toggle open/closed, update fuel prices, verify and complete bookings by token.

### Admin Panel
Approve pending stations, manage users across all roles, full station CRUD, analytics with revenue tracking.

---

## 🏗️ Project Structure

```
Fuel Station/
├── backend/
│   ├── app.py              # FastAPI server (all routes)
│   ├── models.py           # SQLAlchemy models
│   ├── database.py         # DB connection (SQLite / PostgreSQL)
│   ├── seed.py             # Demo data seeder
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Single-page application
│   ├── css/style.css       # Styles
│   └── js/
│       ├── api.js          # API client
│       └── app.js          # UI logic
├── render.yaml             # Render.com deployment config
├── start.bat               # One-click launcher
└── parking.db              # SQLite database
```

---

## 🔌 API Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Register new user |
| POST | `/api/auth/login` | Login (session-based) |
| GET | `/api/auth/me` | Current user info |
| GET | `/api/stations/nearby` | Stations within radius (km) |
| POST | `/api/bookings` | Create booking (auto token) |
| POST | `/api/bookings/verify` | Lookup booking by token |
| PUT | `/api/bookings/{id}/complete` | Complete + free slot |
| PUT | `/api/bookings/{id}/cancel` | Cancel + restore slot |
| GET | `/api/admin/analytics` | Dashboard stats |

Full list at **http://localhost:8000/docs** (Swagger UI)

---

## 🌐 Same Network (LAN)

Run the server, then share `http://YOUR_IP:8000` with teammates (find IP with `ipconfig`).

---

## 🛠️ Built With

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite/PostgreSQL
- **Frontend:** Vanilla JS, Leaflet.js (OpenStreetMap), Font Awesome
- **Auth:** Session-based (Starlette SessionMiddleware)
- **Maps:** OpenStreetMap tiles + Nominatim geocoding

---

<div align="center">
  <p><strong>CSE303 — University Project</strong></p>
  <p>Parking & Fuel Station Management System — Bangladesh</p>
</div>
