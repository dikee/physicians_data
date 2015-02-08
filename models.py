from sqlalchemy import Column, Integer, String  # , DateTime, Table
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship


Base = declarative_base()


class Tract(Base):
    __tablename__ = 'tract'

    id = Column(Integer, primary_key=True)
    state_fp = Column(String)
    county_fp = Column(String)
    tract_ce = Column(String)
    population = Column(String)
    latitude_t = Column(String)
    longitude_t = Column(String)

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
