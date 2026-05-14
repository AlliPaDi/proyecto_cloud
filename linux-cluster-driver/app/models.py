from sqlalchemy import Column, Integer, String, JSON, DECIMAL, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Worker(Base):
    __tablename__ = 'workers'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(50), nullable=False)
    ip_management = Column(String(15), nullable=False)
    total_ram = Column(Integer, nullable=False)
    total_cpu = Column(Integer, nullable=False)
    current_cpu_load = Column(DECIMAL(5, 2), default=0.0)
    current_ram_available = Column(Integer, default=0)
    status = Column(String(20), default='ALIVE')

class Slice(Base):
    __tablename__ = 'slices'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default='PENDING_APPROVAL')

class VirtualMachine(Base):
    __tablename__ = 'virtual_machines'
    id = Column(Integer, primary_key=True)
    slice_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    base_image = Column(String(100), nullable=False)
    ram = Column(Integer, nullable=False)
    vcpu = Column(Integer, nullable=False)
    worker_id = Column(Integer)
    process_id = Column(Integer)
    vnc_port = Column(Integer)
    instance_path = Column(String(255))
    status = Column(String(20), default='PENDING')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    slice_id = Column(Integer, nullable=False)
    vm_id = Column(Integer, nullable=False)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default='PENDING')
    payload = Column(JSON, nullable=False)
    worker_id = Column(Integer)
    error_msg = Column(String)

class Config(Base):
    __tablename__ = 'config'
    key = Column(String(100), primary_key=True)
    value = Column(String, nullable=False)
