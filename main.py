from typing import Annotated
from fastapi import Depends, FastAPI, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from contextlib import asynccontextmanager
from datetime import datetime, date
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

class MetricMinMax(BaseModel):
    metric: str
    min_value: float | None
    max_value: float | None

class SensorMinMax(BaseModel):
    sensor: Sensor
    date: date
    metrics: list[MetricMinMax]

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

# remove sensor_id from inside of latest_measure
@app.get("/sensorList")
async def sensorList(session: SessionDep):
    sensors = session.exec(select(Sensor)).all()
    result = []
    for s in sensors:
        measure = session.exec(
            select(Measure).
            where(Measure.sensor_id == s.sensor_id).
            order_by(Measure.rtime.desc())
        ).first()
        result.append(SensorWithMeasure(sensor_id = s.sensor_id, serial_code = s.serial_code, name = s.name, latest_measure = measure))
    return result

# apply precision from units table
@app.get("/sensorMinMax")
async def sensorMinMax(session: SessionDep, target_date: date = date.today()):
    sensors = session.exec(select(Sensor)).all()
    result = []
    for s in sensors:
        metrics = session.exec(select(Metric)).all()
        metrics_min_max = []
        for m in metrics:
            query_min_value = session.exec(
                    select(Measure.rvalue).
                    where(Measure.sensor_id == s.sensor_id).
                    where(Measure.metric_id == m.metric_id).
                    where(Measure.rtime.like(f"{target_date}%")).
                    order_by(Measure.rvalue)
                ).first()
            if query_min_value:
                query_max_value = session.exec(
                    select(Measure.rvalue).
                    where(Measure.sensor_id == s.sensor_id).
                    where(Measure.metric_id == m.metric_id).
                    where(Measure.rtime.like(f"{target_date}%")).
                    order_by(Measure.rvalue.desc())
                ).first()
                metrics_min_max.append(MetricMinMax(metric = m.metric_name, min_value = query_min_value, max_value = query_max_value))
        result.append(SensorMinMax(sensor = s, date = target_date, metrics = metrics_min_max))
    return result

# add ability to select several sensors and metrics
# if time_to is a date, measures up to previous day 23:59:59 are returned, maybe change that to add the time_to date
@app.get("/measureFilter")
async def measureFilter(session: SessionDep, target_sensor_id: int | None = None, target_metric_id: int | None = None, time_from: datetime | None = None, time_to: datetime | None = None, value_from: float | None = None, value_to: float | None = None):
    query = select(Measure)
    if target_sensor_id is not None:
        query = query.where(Measure.sensor_id == target_sensor_id)
    if target_metric_id is not None:
        query = query.where(Measure.metric_id == target_metric_id)
    if time_from is not None:
        query = query.where(Measure.rtime >= time_from)
    if time_to is not None:
        query = query.where(Measure.rtime <= time_to)
    if value_from is not None:
        query = query.where(Measure.rvalue >= value_from)
    if value_to is not None:
        query = query.where(Measure.rvalue <= value_to)
    measures = session.exec(query).all()
    return measures