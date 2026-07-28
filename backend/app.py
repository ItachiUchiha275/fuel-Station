import math
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_
from starlette.middleware.sessions import SessionMiddleware
from passlib.hash import pbkdf2_sha256 as pwd_hasher

from database import get_db, engine, Base
from models import (
    User, Station, FuelPrice, Booking,
    UserRole, StationType, ApprovalStatus,
    BookingStatus, VehicleType, FuelType,
    generate_token
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Parking & Fuel Station Management")

# Session secret (in production, use env var)
app.add_middleware(SessionMiddleware, secret_key="parking-app-secret-key-change-in-prod")  # swap this with an env var in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


def haversine(lat1, lng1, lat2, lng2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))




class SignupRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    role: str = "driver"
    vehicle_type: Optional[str] = None
    fuel_preference: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    vehicle_type: Optional[str] = None
    fuel_preference: Optional[str] = None


class StationCreate(BaseModel):
    name: str
    address: str
    lat: float
    lng: float
    station_type: str = "parking"
    total_capacity: int = 0
    available_slots: int = 0
    hourly_rate: float = 0.0
    operating_hours: str = "24/7"


class StationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    station_type: Optional[str] = None
    total_capacity: Optional[int] = None
    available_slots: Optional[int] = None
    hourly_rate: Optional[float] = None
    operating_hours: Optional[str] = None


class SlotUpdate(BaseModel):
    delta: int  # +1 or -1


class StatusUpdate(BaseModel):
    is_open: bool


class FuelPriceCreate(BaseModel):
    fuel_type: str
    price_per_liter: float
    date: Optional[str] = None


class FuelPriceUpdate(BaseModel):
    price_per_liter: float


class BookingCreate(BaseModel):
    station_id: int
    start_time: str
    duration_hours: int
    vehicle_type: Optional[str] = None
    payment_method: Optional[str] = "mobile banking(bkash/nagad)"


class TokenLookup(BaseModel):
    token: str




@app.post("/api/auth/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if req.role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="Invalid role")
    hashed = pwd_hasher.hash(req.password)
    user = User(
        name=req.name, email=req.email, phone=req.phone,
        password_hash=hashed, role=req.role,
        vehicle_type=req.vehicle_type, fuel_preference=req.fuel_preference
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not pwd_hasher.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    request.session["user_id"] = user.id
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "role": user.role, "vehicle_type": user.vehicle_type,
        "fuel_preference": user.fuel_preference
    }


@app.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"detail": "Logged out"}


@app.get("/api/auth/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request, db)
        return {
            "id": user.id, "name": user.name, "email": user.email,
            "phone": user.phone, "role": user.role,
            "vehicle_type": user.vehicle_type,
            "fuel_preference": user.fuel_preference,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except HTTPException:
        return {"error": "Not authenticated"}


@app.put("/api/auth/profile")
def update_profile(req: ProfileUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if req.name is not None:
        user.name = req.name
    if req.phone is not None:
        user.phone = req.phone
    if req.vehicle_type is not None:
        user.vehicle_type = req.vehicle_type
    if req.fuel_preference is not None:
        user.fuel_preference = req.fuel_preference
    db.commit()
    return {"detail": "Profile updated"}




@app.post("/api/stations")
def create_station(req: StationCreate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role not in ["operator", "fuel_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only operators and fuel managers can create stations")
    station = Station(
        name=req.name, address=req.address, lat=req.lat, lng=req.lng,
        station_type=req.station_type, total_capacity=req.total_capacity,
        available_slots=req.available_slots, hourly_rate=req.hourly_rate,
        operating_hours=req.operating_hours, provider_id=user.id
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return {
        "id": station.id, "name": station.name,
        "approval_status": station.approval_status
    }


@app.get("/api/stations/mine")
def get_my_stations(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role == "admin":
        stations = db.query(Station).all()
    else:
        stations = db.query(Station).filter(Station.provider_id == user.id).all()
    result = []
    for s in stations:
        fuel_prices = db.query(FuelPrice).filter(FuelPrice.station_id == s.id).all()
        result.append({
            "id": s.id, "name": s.name, "address": s.address,
            "lat": s.lat, "lng": s.lng, "station_type": s.station_type,
            "total_capacity": s.total_capacity,
            "available_slots": s.available_slots,
            "hourly_rate": s.hourly_rate,
            "operating_hours": s.operating_hours,
            "approval_status": s.approval_status,
            "is_open": s.is_open,
            "fuel_prices": [
                {"id": fp.id, "fuel_type": fp.fuel_type,
                 "price_per_liter": fp.price_per_liter, "date": fp.date}
                for fp in fuel_prices
            ]
        })
    return result




@app.get("/api/stations/nearby")
def nearby_stations(
    lat: float, lng: float, radius: float = 5.0,
    vehicle_type: Optional[str] = None,
    fuel_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    stations = db.query(Station).filter(
        and_(
            Station.approval_status == ApprovalStatus.approved.value,
            Station.is_open == True
        )
    ).all()

    result = []
    for s in stations:
        dist = haversine(lat, lng, s.lat, s.lng)
        if dist > radius:
            continue
        fuel_prices = db.query(FuelPrice).filter(FuelPrice.station_id == s.id).all()
        fp_list = [
            {"fuel_type": fp.fuel_type, "price_per_liter": fp.price_per_liter}
            for fp in fuel_prices
        ]
        if fuel_type:
            matching_fuels = [fp for fp in fp_list if fp["fuel_type"].lower() == fuel_type.lower()]
            if not matching_fuels:
                continue
        result.append({
            "id": s.id, "name": s.name, "address": s.address,
            "lat": s.lat, "lng": s.lng, "station_type": s.station_type,
            "total_capacity": s.total_capacity,
            "available_slots": s.available_slots,
            "hourly_rate": s.hourly_rate,
            "operating_hours": s.operating_hours,
            "is_open": s.is_open,
            "distance_km": round(dist, 2),
            "fuel_prices": fp_list
        })

    result.sort(key=lambda x: x["distance_km"])
    return result


@app.get("/api/stations/{station_id}")
def get_station(station_id: int, db: Session = Depends(get_db)):
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    fuel_prices = db.query(FuelPrice).filter(FuelPrice.station_id == station_id).all()
    return {
        "id": station.id, "name": station.name, "address": station.address,
        "lat": station.lat, "lng": station.lng, "station_type": station.station_type,
        "total_capacity": station.total_capacity,
        "available_slots": station.available_slots,
        "hourly_rate": station.hourly_rate,
        "operating_hours": station.operating_hours,
        "approval_status": station.approval_status,
        "is_open": station.is_open,
        "provider_id": station.provider_id,
        "fuel_prices": [
            {"id": fp.id, "fuel_type": fp.fuel_type,
             "price_per_liter": fp.price_per_liter, "date": fp.date}
            for fp in fuel_prices
        ]
    }


@app.put("/api/stations/{station_id}")
def update_station(station_id: int, req: StationUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    if req.name is not None:
        station.name = req.name
    if req.address is not None:
        station.address = req.address
    if req.lat is not None:
        station.lat = req.lat
    if req.lng is not None:
        station.lng = req.lng
    if req.station_type is not None:
        station.station_type = req.station_type
    if req.total_capacity is not None:
        station.total_capacity = req.total_capacity
    if req.available_slots is not None:
        station.available_slots = req.available_slots
    if req.hourly_rate is not None:
        station.hourly_rate = req.hourly_rate
    if req.operating_hours is not None:
        station.operating_hours = req.operating_hours
    db.commit()
    return {"detail": "Station updated"}


@app.delete("/api/stations/{station_id}")
def delete_station(station_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    db.delete(station)
    db.commit()
    return {"detail": "Station deleted"}


@app.put("/api/stations/{station_id}/slots")
def update_slots(station_id: int, req: SlotUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    new_slots = station.available_slots + req.delta
    if new_slots < 0:
        raise HTTPException(status_code=400, detail="Slots cannot be negative")
    if new_slots > station.total_capacity:
        raise HTTPException(status_code=400, detail="Slots cannot exceed total capacity")
    station.available_slots = new_slots
    db.commit()
    return {"available_slots": station.available_slots}


@app.put("/api/stations/{station_id}/status")
def toggle_status(station_id: int, req: StatusUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    station.is_open = req.is_open
    db.commit()
    return {"is_open": station.is_open}




@app.post("/api/stations/{station_id}/fuel-prices")
def add_fuel_price(station_id: int, req: FuelPriceCreate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    fp = FuelPrice(
        station_id=station_id,
        fuel_type=req.fuel_type,
        price_per_liter=req.price_per_liter,
        date=req.date or datetime.utcnow().strftime("%Y-%m-%d")
    )
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return {"id": fp.id, "fuel_type": fp.fuel_type, "price_per_liter": fp.price_per_liter}


@app.get("/api/stations/{station_id}/fuel-prices")
def get_fuel_prices(station_id: int, db: Session = Depends(get_db)):
    return db.query(FuelPrice).filter(FuelPrice.station_id == station_id).all()


@app.put("/api/fuel-prices/{price_id}")
def update_fuel_price(price_id: int, req: FuelPriceUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    fp = db.query(FuelPrice).filter(FuelPrice.id == price_id).first()
    if not fp:
        raise HTTPException(status_code=404, detail="Fuel price not found")
    station = db.query(Station).filter(Station.id == fp.station_id).first()
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    fp.price_per_liter = req.price_per_liter
    db.commit()
    return {"detail": "Fuel price updated"}


@app.delete("/api/fuel-prices/{price_id}")
def delete_fuel_price(price_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    fp = db.query(FuelPrice).filter(FuelPrice.id == price_id).first()
    if not fp:
        raise HTTPException(status_code=404, detail="Fuel price not found")
    station = db.query(Station).filter(Station.id == fp.station_id).first()
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    db.delete(fp)
    db.commit()
    return {"detail": "Fuel price deleted"}




@app.post("/api/bookings")
def create_booking(req: BookingCreate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    station = db.query(Station).filter(Station.id == req.station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    if station.approval_status != ApprovalStatus.approved.value:
        raise HTTPException(status_code=400, detail="Station not approved")
    if not station.is_open:
        raise HTTPException(status_code=400, detail="Station is closed")
    if station.available_slots <= 0:
        raise HTTPException(status_code=400, detail="No available slots")

    start_dt = datetime.fromisoformat(req.start_time)
    cost = req.duration_hours * station.hourly_rate

    token = generate_token()
    while db.query(Booking).filter(Booking.token == token).first():
        token = generate_token()

    booking = Booking(
        station_id=req.station_id,
        user_id=user.id,
        token=token,
        start_time=start_dt,
        duration_hours=req.duration_hours,
        cost=cost,
        vehicle_type=req.vehicle_type or user.vehicle_type,
        payment_method=req.payment_method or "mobile banking(bkash/nagad)",
        status=BookingStatus.active.value
    )
    db.add(booking)
    station.available_slots -= 1
    db.commit()
    db.refresh(booking)

    return {
        "id": booking.id,
        "token": booking.token,
        "start_time": booking.start_time.isoformat(),
        "duration_hours": booking.duration_hours,
        "cost": booking.cost,
        "status": booking.status,
        "payment_method": booking.payment_method
    }


@app.get("/api/bookings/mine")
def get_my_bookings(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    bookings = db.query(Booking).filter(Booking.user_id == user.id).order_by(Booking.created_at.desc()).all()
    result = []
    for b in bookings:
        station = db.query(Station).filter(Station.id == b.station_id).first()
        now = datetime.utcnow()
        end_time = b.start_time + timedelta(hours=b.duration_hours)
        remaining_minutes = int((end_time - now).total_seconds() / 60) if end_time > now else 0
        is_overtime = now > end_time and b.status == BookingStatus.active.value
        overtime_hours = 0
        overtime_charge = 0
        if is_overtime and station:
            overtime_hours = math.ceil((now - end_time).total_seconds() / 3600)
            overtime_charge = overtime_hours * station.hourly_rate

        result.append({
            "id": b.id,
            "token": b.token,
            "station_name": station.name if station else "Unknown",
            "station_id": b.station_id,
            "start_time": b.start_time.isoformat(),
            "duration_hours": b.duration_hours,
            "cost": b.cost,
            "overtime_hours": b.overtime_hours or overtime_hours,
            "overtime_charge": b.overtime_charge or overtime_charge,
            "status": b.status,
            "vehicle_type": b.vehicle_type,
            "payment_method": b.payment_method,
            "remaining_minutes": remaining_minutes,
            "is_overtime": is_overtime,
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    return result


@app.get("/api/bookings/{token}")
def get_booking_by_token(token: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.token == token).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    station = db.query(Station).filter(Station.id == booking.station_id).first()
    return {
        "id": booking.id,
        "token": booking.token,
        "station_id": booking.station_id,
        "station_name": station.name if station else "Unknown",
        "user_id": booking.user_id,
        "start_time": booking.start_time.isoformat(),
        "duration_hours": booking.duration_hours,
        "cost": booking.cost,
        "status": booking.status,
        "vehicle_type": booking.vehicle_type
    }




@app.post("/api/bookings/verify")
def verify_booking(req: TokenLookup, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    booking = db.query(Booking).filter(Booking.token == req.token).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    station = db.query(Station).filter(Station.id == booking.station_id).first()
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    return {
        "id": booking.id,
        "token": booking.token,
        "station_name": station.name if station else "Unknown",
        "start_time": booking.start_time.isoformat(),
        "duration_hours": booking.duration_hours,
        "cost": booking.cost,
        "status": booking.status,
        "vehicle_type": booking.vehicle_type
    }


@app.put("/api/bookings/{booking_id}/complete")
def complete_booking(booking_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    station = db.query(Station).filter(Station.id == booking.station_id).first()
    if station.provider_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your station")
    if booking.status != BookingStatus.active.value:
        raise HTTPException(status_code=400, detail="Booking is not active")

    # see if they stayed past their time
    now = datetime.utcnow()
    end_time = booking.start_time + timedelta(hours=booking.duration_hours)
    if now > end_time:
        overtime_hours = math.ceil((now - end_time).total_seconds() / 3600)
        booking.overtime_hours = overtime_hours
        booking.overtime_charge = overtime_hours * station.hourly_rate

    booking.status = BookingStatus.completed.value
    station.available_slots += 1
    db.commit()
    return {"detail": "Booking completed", "token": booking.token}


@app.put("/api/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    station = db.query(Station).filter(Station.id == booking.station_id).first()
    if station.provider_id != user.id and user.role != "admin" and booking.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if booking.status != BookingStatus.active.value:
        raise HTTPException(status_code=400, detail="Booking is not active")

    booking.status = BookingStatus.canceled.value
    station.available_slots += 1
    db.commit()
    return {"detail": "Booking canceled", "token": booking.token}




@app.get("/api/admin/pending-approvals")
def pending_approvals(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    stations = db.query(Station).filter(
        Station.approval_status == ApprovalStatus.pending.value
    ).all()
    result = []
    for s in stations:
        provider = db.query(User).filter(User.id == s.provider_id).first()
        result.append({
            "id": s.id,
            "name": s.name,
            "address": s.address,
            "lat": s.lat,
            "lng": s.lng,
            "station_type": s.station_type,
            "provider_name": provider.name if provider else "Unknown",
            "provider_email": provider.email if provider else "Unknown",
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
    return result


@app.put("/api/admin/stations/{station_id}/approve")
def approve_station(station_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    station.approval_status = ApprovalStatus.approved.value
    db.commit()
    return {"detail": "Station approved", "name": station.name}


@app.put("/api/admin/stations/{station_id}/reject")
def reject_station(station_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    station.approval_status = ApprovalStatus.rejected.value
    db.commit()
    return {"detail": "Station rejected", "name": station.name}


@app.get("/api/admin/users")
def admin_list_users(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    search = request.query_params.get("search")
    role_filter = request.query_params.get("role")
    query = db.query(User)
    if search:
        query = query.filter(
            User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )
    if role_filter:
        query = query.filter(User.role == role_filter)
    users = query.order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id, "name": u.name, "email": u.email,
            "phone": u.phone, "role": u.role,
            "vehicle_type": u.vehicle_type,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]


@app.get("/api/admin/users/{user_id}")
def admin_get_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": target.id, "name": target.name, "email": target.email,
        "phone": target.phone, "role": target.role,
        "vehicle_type": target.vehicle_type,
        "fuel_preference": target.fuel_preference,
        "created_at": target.created_at.isoformat() if target.created_at else None
    }


@app.put("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, req: SignupRequest, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if req.name is not None:
        target.name = req.name
    if req.email is not None:
        target.email = req.email
    if req.phone is not None:
        target.phone = req.phone
    if req.role is not None:
        target.role = req.role
    if req.vehicle_type is not None:
        target.vehicle_type = req.vehicle_type
    if req.fuel_preference is not None:
        target.fuel_preference = req.fuel_preference
    if req.password:
        target.password_hash = pwd_hasher.hash(req.password)
    db.commit()
    return {"detail": "User updated"}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "admin" and db.query(User).filter(User.role == "admin").count() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete last admin")
    db.delete(target)
    db.commit()
    return {"detail": "User deleted"}


@app.get("/api/admin/stations")
def admin_list_stations(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    stations = db.query(Station).order_by(Station.created_at.desc()).all()
    result = []
    for s in stations:
        provider = db.query(User).filter(User.id == s.provider_id).first()
        result.append({
            "id": s.id, "name": s.name, "address": s.address,
            "station_type": s.station_type,
            "approval_status": s.approval_status,
            "is_open": s.is_open,
            "total_capacity": s.total_capacity,
            "available_slots": s.available_slots,
            "hourly_rate": s.hourly_rate,
            "provider_name": provider.name if provider else "Unknown",
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
    return result


@app.get("/api/admin/analytics")
def admin_analytics(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    total_drivers = db.query(User).filter(User.role == "driver").count()
    total_approved_stations = db.query(Station).filter(
        Station.approval_status == ApprovalStatus.approved.value
    ).count()
    total_pending_stations = db.query(Station).filter(
        Station.approval_status == ApprovalStatus.pending.value
    ).count()
    total_operators = db.query(User).filter(
        User.role.in_(["operator", "fuel_manager"])
    ).count()
    active_bookings = db.query(Booking).filter(
        Booking.status == BookingStatus.active.value
    ).count()
    completed_bookings = db.query(Booking).filter(
        Booking.status == BookingStatus.completed.value
    ).count()
    canceled_bookings = db.query(Booking).filter(
        Booking.status == BookingStatus.canceled.value
    ).count()
    revenue_result = db.query(Booking).filter(
        Booking.status == BookingStatus.completed.value
    ).all()
    total_revenue = sum(b.cost + (b.overtime_charge or 0) for b in revenue_result)

    return {
        "total_drivers": total_drivers,
        "total_operators": total_operators,
        "total_approved_stations": total_approved_stations,
        "total_pending_stations": total_pending_stations,
        "active_bookings": active_bookings,
        "completed_bookings": completed_bookings,
        "canceled_bookings": canceled_bookings,
        "total_revenue": round(total_revenue, 2)
    }


def seed_demo_data(db):
    if db.query(Station).count() > 0:
        return
    for u in [
        {"name":"Demo Driver","email":"driver@test.com","phone":"+8801722222222","password":"pass123","role":"driver"},
        {"name":"Demo Operator","email":"operator@test.com","phone":"+8801711111111","password":"pass123","role":"operator"},
    ]:
        if not db.query(User).filter(User.email == u["email"]).first():
            db.add(User(name=u["name"], email=u["email"], phone=u["phone"],
                        password_hash=pwd_hasher.hash(u["password"]), role=u["role"]))
    db.commit()
    operator_id = db.query(User).filter(User.email == "operator@test.com").first().id

    stations_data = [
        {"name":"Gulshan Parking Complex","address":"Gulshan 1, Dhaka 1212","lat":23.7925,"lng":90.4078,"type":"parking","cap":80,"slots":45,"rate":60,"hours":"6AM-12AM"},
        {"name":"Banani Parking Zone","address":"Banani 11, Dhaka 1213","lat":23.7939,"lng":90.4045,"type":"parking","cap":60,"slots":32,"rate":50,"hours":"24/7"},
        {"name":"Dhanmondi Parking Center","address":"Road 2, Dhanmondi, Dhaka 1205","lat":23.7465,"lng":90.3746,"type":"parking","cap":100,"slots":70,"rate":40,"hours":"7AM-11PM"},
        {"name":"Motijheel Parking Tower","address":"Motijheel C/A, Dhaka 1000","lat":23.7330,"lng":90.4174,"type":"parking","cap":90,"slots":55,"rate":55,"hours":"8AM-9PM"},
        {"name":"Uttara Parking Hub","address":"Sector 3, Uttara, Dhaka 1230","lat":23.8759,"lng":90.3795,"type":"parking","cap":120,"slots":85,"rate":35,"hours":"6AM-12AM"},
        {"name":"Mirpur Parking Plaza","address":"Mirpur 10, Dhaka 1216","lat":23.8069,"lng":90.3685,"type":"parking","cap":70,"slots":40,"rate":30,"hours":"7AM-10PM"},
        {"name":"Padma Fuel Station","address":"Gulshan Avenue, Dhaka 1212","lat":23.7950,"lng":90.4100,"type":"fuel","cap":0,"slots":0,"rate":0,"hours":"24/7"},
        {"name":"Jamuna Fuel Point","address":"Dhanmondi 27, Dhaka 1205","lat":23.7440,"lng":90.3700,"type":"fuel","cap":0,"slots":0,"rate":0,"hours":"7AM-11PM"},
        {"name":"Agrabad Parking Complex","address":"Agrabad C/A, Chattogram 4100","lat":22.3200,"lng":91.8000,"type":"parking","cap":75,"slots":40,"rate":50,"hours":"7AM-11PM"},
        {"name":"GEC Parking Station","address":"GEC Circle, Chattogram 4000","lat":22.3568,"lng":91.7832,"type":"parking","cap":60,"slots":35,"rate":45,"hours":"8AM-10PM"},
        {"name":"Karnafuli Service Station","address":"Karnafuli Lane, Chattogram 4100","lat":22.3100,"lng":91.8150,"type":"both","cap":30,"slots":18,"rate":40,"hours":"24/7"},
        {"name":"Shaheb Bazar Parking","address":"Shaheb Bazar, Rajshahi 6100","lat":24.3700,"lng":88.6000,"type":"parking","cap":50,"slots":28,"rate":35,"hours":"7AM-10PM"},
        {"name":"Khulna Parking Station","address":"Sher-E-Bangla Road, Khulna 9100","lat":22.8450,"lng":89.5400,"type":"parking","cap":55,"slots":30,"rate":35,"hours":"7AM-11PM"},
        {"name":"Barisal Parking Complex","address":"Sadar Road, Barisal 8200","lat":22.7010,"lng":90.3715,"type":"parking","cap":35,"slots":20,"rate":25,"hours":"7AM-9PM"},
        {"name":"Sylhet City Parking","address":"Zindabazar, Sylhet 3100","lat":24.8940,"lng":91.8680,"type":"parking","cap":50,"slots":30,"rate":40,"hours":"7AM-11PM"},
        {"name":"Surma Service Station","address":"Surma Road, Sylhet 3100","lat":24.8880,"lng":91.8600,"type":"both","cap":20,"slots":12,"rate":35,"hours":"7AM-11PM"},
        {"name":"Rangpur Parking Plaza","address":"Pirjabad, Rangpur 5400","lat":25.7460,"lng":89.2520,"type":"parking","cap":40,"slots":25,"rate":25,"hours":"7AM-9PM"},
        {"name":"Mymensingh Parking Center","address":"Kachijhuli, Mymensingh 2200","lat":24.7530,"lng":90.4090,"type":"parking","cap":45,"slots":28,"rate":30,"hours":"7AM-10PM"},
    ]
    for s in stations_data:
        station = Station(name=s["name"], address=s["address"], lat=s["lat"], lng=s["lng"],
                          station_type=s["type"], total_capacity=s["cap"], available_slots=s["slots"],
                          hourly_rate=s["rate"], operating_hours=s["hours"],
                          approval_status="Approved", is_open=True, provider_id=operator_id)
        db.add(station)
        db.flush()
        if s["type"] in ("fuel", "both"):
            for ft, price in [("Petrol", 115), ("Octane", 125), ("Diesel", 108), ("CNG", 55)]:
                db.add(FuelPrice(station_id=station.id, fuel_type=ft, price_per_liter=price, date="2026-07-29"))
    db.commit()

@app.on_event("startup")
def startup():
    db = next(get_db())
    if not db.query(User).filter(User.email == "admin@parking.com").first():
        db.add(User(name="System Admin", email="admin@parking.com",
                    phone="+8801700000000", password_hash=pwd_hasher.hash("admin123"),
                    role="admin"))
        db.commit()
    seed_demo_data(db)
    db.close()


app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
