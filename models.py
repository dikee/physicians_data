from sqlalchemy import Column, Float, Integer, String, ForeignKey  # , DateTime, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class TractCode(Base):
    __tablename__ = 'tract_code'

    id = Column(Integer, primary_key=True)
    tract_code = Column(String)
    tracts = relationship('Tract', backref='tract_code')
    physicians = relationship('Physicians', backref='tract_code')
    two_stage = Column(Float)

class Tract(Base):
    __tablename__ = 'tract'

    id = Column(Integer, primary_key=True)
    state_fp = Column(String)
    county_fp = Column(String)
    tract_ce = Column(String)
    population = Column(String)
    latitude_t = Column(String)
    longitude_t = Column(String)
    tract_code_id = Column(Integer, ForeignKey('tract_code.id'))

    def _three_digits(self, value):
        value = str(int(value))
        while len(value) < 3:
            '0' + value
        return value


class Physicians(Base):
    __tablename__ = 'physicians'

    id = Column(Integer, primary_key=True)
    object_id = Column(String)
    latitude_p = Column(String)
    longitude_p = Column(String)
    city = Column(String)
    state = Column(String)
    zipcode = Column(String)
    tract_code_id = Column(Integer, ForeignKey('tract_code.id'))
    docs_within = Column(Integer)
    docs_within_10 = Column(Integer)
    docs_within_15 = Column(Integer)
    docs_within_45 = Column(Integer)
    docs_within_60 = Column(Integer)
    tracts_within = Column(Integer)
    tracts_within_10 = Column(Integer)
    tracts_within_15 = Column(Integer)
    tracts_within_45 = Column(Integer)
    tracts_within_60 = Column(Integer)
    ratio_10 = Column(Float)
    ratio_15 = Column(Float)
    ratio_30 = Column(Float)
    ratio_45 = Column(Float)
    ratio_60 = Column(Float)

class WithinMiles(Base):
    __tablename__ = 'within_miles'

    id = Column(Integer, primary_key=True)
    state_fp = Column(String)
    county_fp = Column(String)
    tract_ce = Column(String)
    population = Column(String)
    latitude_t = Column(String)
    longitude_t = Column(String)

    object_id = Column(String)
    latitude_p = Column(String)
    longitude_p = Column(String)
    city = Column(String)
    state = Column(String)
    zipcode = Column(String)
    miles = Column(Integer)
