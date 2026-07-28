import random
import string
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base
import enum


class UserRole(str, enum.Enum):
    driver = "driver"
    operator = "operator"
    fuel_manager = "fuel_manager"
    admin = "admin"


class StationType(str, enum.Enum):
    parking = "parking"
    fuel = "fuel"
    both = "both"


class ApprovalStatus(str, enum.Enum):
    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"


class BookingStatus(str, enum.Enum):
    active = "Active"
    completed = "Completed"
    canceled = "Canceled"


class VehicleType(str, enum.Enum):
    car = "Car"
    motorcycle = "Motorcycle"


class FuelType(str, enum.Enum):
    petrol = "Petrol"
    octane = "Octane"
    diesel = "Diesel"
    cng = "CNG"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.driver.value)
    vehicle_type = Column(String(20), nullable=True)
    fuel_preference = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    stations = relationship("Station", back_populates="provider")
    bookings = relationship("Booking", back_populates="user")


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=False)
    lat = Column(Float, nullable=False, index=True)
    lng = Column(Float, nullable=False, index=True)
    station_type = Column(String(20), nullable=False, default=StationType.parking.value)
    total_capacity = Column(Integer, default=0)
    available_slots = Column(Integer, default=0)
    hourly_rate = Column(Float, default=0.0)
    operating_hours = Column(String(100), default="24/7")
    approval_status = Column(String(20), nullable=False, default=ApprovalStatus.pending.value)
    is_open = Column(Boolean, default=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    provider = relationship("User", back_populates="stations")
    fuel_prices = relationship("FuelPrice", back_populates="station", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="station")


class FuelPrice(Base):
    __tablename__ = "fuel_prices"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    fuel_type = Column(String(20), nullable=False)
    price_per_liter = Column(Float, nullable=False)
    date = Column(String(20), default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    created_at = Column(DateTime, default=datetime.utcnow)

    station = relationship("Station", back_populates="fuel_prices")

    __table_args__ = (
        # Index for fuel type lookups per station
        None,
    )


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(10), unique=True, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    duration_hours = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    overtime_hours = Column(Integer, default=0)
    overtime_charge = Column(Float, default=0.0)
    status = Column(String(20), nullable=False, default=BookingStatus.active.value)
    payment_method = Column(String(50), default="mobile banking(bkash/nagad)")
    vehicle_type = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    station = relationship("Station", back_populates="bookings")
    user = relationship("User", back_populates="bookings")


def generate_token():
    """Generate a unique 6-char token like PRK-892"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    digits = ''.join(random.choices(string.digits, k=3))
    return f"{letters}-{digits}"
