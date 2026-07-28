import sys
from database import engine, Base
from models import User, Station, FuelPrice, Booking

# gotta import models so Base knows about all the tables

def init_database():
    Base.metadata.create_all(bind=engine)
    print("[OK] Database created successfully!", file=sys.stderr)
    print()
    print("=== SCHEMA ===")
    for table_name, table in Base.metadata.tables.items():
        print(f"\n--- {table_name} ---")
        for col in table.columns:
            pk = " PK" if col.primary_key else ""
            fk_set = col.foreign_keys
            fk = ""
            if fk_set:
                fk_ref = list(fk_set)[0]
                fk = f" FK->{fk_ref.column.table.name}.{fk_ref.column.name}"
            nullable = "" if col.nullable else " NOT NULL"
            default = ""
            if col.default is not None and col.default.arg is not None:
                default = f" DEFAULT {col.default.arg}"
            print(f"  {col.name}: {col.type}{pk}{fk}{nullable}{default}")
        for idx in table.indexes:
            print(f"  INDEX: {idx.name} on {[c.name for c in idx.columns]}")


if __name__ == "__main__":
    init_database()
