from sqlacademy import create_engine, Column, Integer, String, DateTime,Text, Boolean, FLoat
from sqlacademy.ext.declarative import declarative_base
from sqlacademy.orm import sessionmaker
from datetime import datetime

# Creates employee.db in the data/ directory
engine = create_engine('sqlite:///data/employee.db', 
                       connect_args={"check_same_thread":False} ,echo=True) # needed for fast api

SessionLoal= sessionmaker(bind=engine)
Base= declarative_base()

# class Employee(Base):
# class AuditLog(Base):

