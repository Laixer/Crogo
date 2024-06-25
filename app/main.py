import datetime
from typing import List, Union
from pydantic import BaseModel

from fastapi import FastAPI, Header, status

app = FastAPI()


class Metadata(BaseModel):
    hostname: str
    kernel: str
    datetime: datetime.datetime


class VMS(BaseModel):
    cpu1: float
    cpu5: float
    cpu15: float
    mem_used: int
    mem_total: int
    uptime: int


class Instance(BaseModel):
    id: str
    model: str
    # version: str
    serial_number: str


class Probe(BaseModel):
    meta: Metadata
    instance: Instance
    host: Union[VMS, None] = None


# @app.get("/")
# def read_root():
#     return {"Hello": "World"}


# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}


@app.post("/probe", status_code=status.HTTP_201_CREATED)
async def create_probe(probe: Probe, x_instance_id: str = Header()):
    print(probe)
    print(x_instance_id)
