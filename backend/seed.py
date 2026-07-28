from database import SessionLocal, engine, Base
from models import User, Station, FuelPrice, Booking
Base.metadata.create_all(bind=engine)
from models import User, Station, FuelPrice, Booking
from passlib.hash import pbkdf2_sha256 as pwd_hasher
from datetime import datetime

db = SessionLocal()

# Ensure admin exists
if not db.query(User).filter(User.email == "admin@parking.com").first():
    db.add(User(name="System Admin", email="admin@parking.com",
                phone="+8801700000000", password_hash=pwd_hasher.hash("admin123"),
                role="admin"))

# Ensure operator exists
if not db.query(User).filter(User.email == "operator@test.com").first():
    db.add(User(name="Demo Operator", email="operator@test.com",
                phone="+8801711111111", password_hash=pwd_hasher.hash("pass123"),
                role="operator"))

# Ensure driver exists
if not db.query(User).filter(User.email == "driver@test.com").first():
    db.add(User(name="Demo Driver", email="driver@test.com",
                phone="+8801722222222", password_hash=pwd_hasher.hash("pass123"),
                role="driver"))

db.commit()

operator = db.query(User).filter(User.email == "operator@test.com").first().id

stations = [
    # === DHAKA DIVISION ===
    {"name": "Gulshan Parking Complex", "address": "Gulshan 1, Dhaka 1212", "lat": 23.7925, "lng": 90.4078, "type": "parking", "cap": 80, "slots": 45, "rate": 60, "hours": "6AM-12AM"},
    {"name": "Banani Parking Zone", "address": "Banani 11, Dhaka 1213", "lat": 23.7939, "lng": 90.4045, "type": "parking", "cap": 60, "slots": 32, "rate": 50, "hours": "24/7"},
    {"name": "Dhanmondi Parking Center", "address": "Road 2, Dhanmondi, Dhaka 1205", "lat": 23.7465, "lng": 90.3746, "type": "parking", "cap": 100, "slots": 70, "rate": 40, "hours": "7AM-11PM"},
    {"name": "Motijheel Parking Tower", "address": "Motijheel C/A, Dhaka 1000", "lat": 23.7330, "lng": 90.4174, "type": "parking", "cap": 90, "slots": 55, "rate": 55, "hours": "8AM-9PM"},
    {"name": "Uttara Parking Hub", "address": "Sector 3, Uttara, Dhaka 1230", "lat": 23.8759, "lng": 90.3795, "type": "parking", "cap": 120, "slots": 85, "rate": 35, "hours": "6AM-12AM"},
    {"name": "Mirpur Parking Plaza", "address": "Mirpur 10, Dhaka 1216", "lat": 23.8069, "lng": 90.3685, "type": "parking", "cap": 70, "slots": 40, "rate": 30, "hours": "7AM-10PM"},
    {"name": "Padma Fuel Station", "address": "Gulshan Avenue, Dhaka 1212", "lat": 23.7950, "lng": 90.4100, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "24/7"},
    {"name": "Jamuna Fuel Point", "address": "Dhanmondi 27, Dhaka 1205", "lat": 23.7440, "lng": 90.3700, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "7AM-11PM"},
    # === CHATTOGRAM DIVISION ===
    {"name": "Agrabad Parking Complex", "address": "Agrabad C/A, Chattogram 4100", "lat": 22.3200, "lng": 91.8000, "type": "parking", "cap": 75, "slots": 40, "rate": 50, "hours": "7AM-11PM"},
    {"name": "GEC Parking Station", "address": "GEC Circle, Chattogram 4000", "lat": 22.3568, "lng": 91.7832, "type": "parking", "cap": 60, "slots": 35, "rate": 45, "hours": "8AM-10PM"},
    {"name": "Chittagong Port Parking", "address": "Port Area, Chattogram 4100", "lat": 22.2950, "lng": 91.7900, "type": "parking", "cap": 100, "slots": 65, "rate": 40, "hours": "24/7"},
    {"name": "Halishahar Fuel Point", "address": "Halishahar, Chattogram 4225", "lat": 22.3400, "lng": 91.7700, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "6AM-11PM"},
    {"name": "Karnafuli Service Station", "address": "Karnafuli Lane, Chattogram 4100", "lat": 22.3100, "lng": 91.8150, "type": "both", "cap": 30, "slots": 18, "rate": 40, "hours": "24/7"},
    # === RAJSHAHI DIVISION ===
    {"name": "Shaheb Bazar Parking", "address": "Shaheb Bazar, Rajshahi 6100", "lat": 24.3700, "lng": 88.6000, "type": "parking", "cap": 50, "slots": 28, "rate": 35, "hours": "7AM-10PM"},
    {"name": "Rajshahi City Center Parking", "address": "RCC More, Rajshahi 6100", "lat": 24.3750, "lng": 88.5800, "type": "parking", "cap": 45, "slots": 25, "rate": 30, "hours": "8AM-9PM"},
    {"name": "Padma Filling Station", "address": "Rajshahi Road, Rajshahi 6100", "lat": 24.3650, "lng": 88.5900, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "6AM-11PM"},
    # === KHULNA DIVISION ===
    {"name": "Khulna Parking Station", "address": "Sher-E-Bangla Road, Khulna 9100", "lat": 22.8450, "lng": 89.5400, "type": "parking", "cap": 55, "slots": 30, "rate": 35, "hours": "7AM-11PM"},
    {"name": "KDA Avenue Parking", "address": "KDA Avenue, Khulna 9100", "lat": 22.8350, "lng": 89.5550, "type": "parking", "cap": 40, "slots": 22, "rate": 30, "hours": "8AM-10PM"},
    {"name": "Rupsha Fuel Station", "address": "Rupsha Ferry, Khulna 9200", "lat": 22.8200, "lng": 89.5700, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "24/7"},
    # === BARISAL DIVISION ===
    {"name": "Barisal Parking Complex", "address": "Sadar Road, Barisal 8200", "lat": 22.7010, "lng": 90.3715, "type": "parking", "cap": 35, "slots": 20, "rate": 25, "hours": "7AM-9PM"},
    {"name": "Nathullabad Fuel Point", "address": "Nathullabad, Barisal 8200", "lat": 22.7100, "lng": 90.3650, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "6AM-10PM"},
    # === SYLHET DIVISION ===
    {"name": "Sylhet City Parking", "address": "Zindabazar, Sylhet 3100", "lat": 24.8940, "lng": 91.8680, "type": "parking", "cap": 50, "slots": 30, "rate": 40, "hours": "7AM-11PM"},
    {"name": "Khadimnagar Parking", "address": "Khadimnagar, Sylhet 3100", "lat": 24.9200, "lng": 91.8900, "type": "parking", "cap": 30, "slots": 18, "rate": 30, "hours": "8AM-10PM"},
    {"name": "Sylhet Fuel Center", "address": "Upashahar, Sylhet 3100", "lat": 24.9000, "lng": 91.8750, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "24/7"},
    {"name": "Surma Service Station", "address": "Surma Road, Sylhet 3100", "lat": 24.8880, "lng": 91.8600, "type": "both", "cap": 20, "slots": 12, "rate": 35, "hours": "7AM-11PM"},
    # === RANGPUR DIVISION ===
    {"name": "Rangpur Parking Plaza", "address": "Pirjabad, Rangpur 5400", "lat": 25.7460, "lng": 89.2520, "type": "parking", "cap": 40, "slots": 25, "rate": 25, "hours": "7AM-9PM"},
    {"name": "Rangpur Fuel Station", "address": "Station Road, Rangpur 5400", "lat": 25.7550, "lng": 89.2400, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "6AM-11PM"},
    # === MYMENSINGH DIVISION ===
    {"name": "Mymensingh Parking Center", "address": "Kachijhuli, Mymensingh 2200", "lat": 24.7530, "lng": 90.4090, "type": "parking", "cap": 45, "slots": 28, "rate": 30, "hours": "7AM-10PM"},
    {"name": "Brahmaputra Fuel Point", "address": "Bhaluka Road, Mymensingh 2200", "lat": 24.7400, "lng": 90.4200, "type": "fuel", "cap": 0, "slots": 0, "rate": 0, "hours": "6AM-10PM"},
]

for s in stations:
    existing = db.query(Station).filter(Station.name == s["name"]).first()
    if existing:
        continue
    station = Station(
        name=s["name"], address=s["address"], lat=s["lat"], lng=s["lng"],
        station_type=s["type"], total_capacity=s["cap"], available_slots=s["slots"],
        hourly_rate=s["rate"], operating_hours=s["hours"],
        approval_status="Approved", is_open=True, provider_id=operator
    )
    db.add(station)
    db.flush()

    # Add fuel prices for fuel stations
    if s["type"] in ("fuel", "both"):
        for ft, price in [("Petrol", 115), ("Octane", 125), ("Diesel", 108), ("CNG", 55)]:
            db.add(FuelPrice(station_id=station.id, fuel_type=ft, price_per_liter=price, date="2026-07-29"))

db.commit()
db.close()

print("Database seeded with 30+ stations across all 8 divisions of Bangladesh!")
print("\nLogin credentials:")
print("  Admin:   admin@parking.com / admin123")
print("  Driver:  driver@test.com   / pass123")
print("  Operator: operator@test.com / pass123")
