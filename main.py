from typing import Annotated
from fastapi import Depends, FastAPI, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from contextlib import asynccontextmanager
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import desc

class Unit(SQLModel, table=True):
    __tablename__ = "units"
    unit_id: int = Field(primary_key=True)
    unit_name: str = Field(index=True)
    precision: int = Field(index=True)
     
class Sensor(SQLModel, table=True):
    __tablename__ = "sensors"
    sensor_id: int = Field(primary_key=True)
    serial_code: str = Field(index=True)
    name: str = Field(index=True)
     
class Metric(SQLModel, table=True):
    __tablename__ = "metrics"
    metric_id: int = Field(primary_key=True)
    metric_name: str = Field(index=True)
    unit_id: int = Field(foreign_key="units.unit_id")

class Measure(SQLModel, table=True):
    __tablename__ = "measures"
    reading_id: int = Field(primary_key=True)
    sensor_id: int = Field(foreign_key="sensors.sensor_id")
    metric_id: int = Field(foreign_key="metrics.metric_id")
    rtime: datetime = Field(index=True)
    rvalue: float = Field(index=True)

class SensorWithMeasure(BaseModel):
    sensor_id: int
    serial_code: str
    name: str
    latest_measure: Measure | None

sqlite_file_name = "aranet.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root(session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=3)] = 3) -> dict[str, Any]:
    measures = session.exec(select(Measure).offset(offset).limit(limit)).all()
    metrics = session.exec(select(Metric).offset(offset).limit(limit)).all()
    sensors = session.exec(select(Sensor).offset(offset).limit(limit)).all()
    units = session.exec(select(Unit).offset(offset).limit(limit)).all()
    return {"measures": measures, "metrics": metrics, "sensors": sensors, "units": units}

@app.get("/sensorList")
async def sensorList(session: SessionDep):
    sensors = session.exec(select(Sensor)).all()
    result = []
    for sensor in sensors:
        measure = session.exec(select(Measure).where(Measure.sensor_id == sensor.sensor_id).order_by(Measure.rtime.desc())).first()
        result.append(SensorWithMeasure(sensor_id = sensor.sensor_id, serial_code = sensor.serial_code, name = sensor.name, latest_measure = measure))
    return result