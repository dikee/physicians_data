from math import radians, cos, sin, asin, sqrt

from models import Physicians, Tract, WithinMiles

import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://dkalu:nigeria@localhost/docsdb")
Session = sessionmaker(bind=engine)


Session.configure(bind=engine)
session = Session()


def haversine(lon1, lat1, lon2, lat2):
    """
    http://stackoverflow.com/questions/15736995/
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    lon1, lat1, lon2, lat2 = float(lon1), float(lat1), float(lon2), float(lat2)
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    miles = 3956 * c
    return int(miles)


def _three_digits(value):
    value = str(int(value))
    while len(value) < 3:
        value = '0' + value
    return value


def unpack_centroids():
    keys = ['state_fp', 'county_fp', 'tract_ce', 'population',
            'latitude_t', 'longitude_t']
    create_obj = []

    df = pd.read_csv('centroidspop.csv')
    print 'Starting with centroids'
    for data in df.values.tolist():
        values = dict(zip(keys, data))
        new_tract = Tract(
            state_fp=str(int(values['state_fp'])),
            county_fp=_three_digits(values['county_fp']),
            tract_ce=str(int(values['tract_ce'])),
            population=str(int(values['population'])),
            latitude_t=str(values['latitude_t']),
            longitude_t=str(values['longitude_t'])
        )
        create_obj.append(new_tract)
    session.add_all(create_obj)
    session.commit()
    print 'Done with centroids'


def unpack_physicians():
    keys = ['object_id', 'longitude_p', 'latitude_p',
            'city', 'state', 'zipcode']
    create_obj = []

    df = pd.read_csv('geo_coded_physicians.csv')
    print 'Starting with physicians'
    for data in df.values.tolist():
        values = dict(zip(keys, data))
        new_physician = Physicians(
            object_id=str(int(values['object_id'])),
            latitude_p=values['latitude_p'],
            longitude_p=values['longitude_p'],
            city=values['city'],
            state=values['state'],
            zipcode=str(values['zipcode'])
        )
        create_obj.append(new_physician)
    session.add_all(create_obj)
    session.commit()
    print 'Done with Physicians'


def populate_distance_table():
    tracts = session.query(Tract).all()
    physicians = session.query(Physicians).all()

    total_tracts = len(tracts)

    count = 1
    for tract in tracts:
        print 'Starting Tract: %s: %s of %s' % (str(tract.tract_ce), count, total_tracts)
        state_fp = tract.state_fp
        county_fp = tract.county_fp
        tract_ce = tract.tract_ce
        population = tract.population
        latitude_t = tract.latitude_t
        longitude_t = tract.longitude_t

        create_obj = []
        for physician in physicians:
            object_id = physician.object_id
            latitude_p = physician.latitude_p
            longitude_p = physician.longitude_p
            city = physician.city
            state = physician.state
            zipcode = physician.zipcode

            miles = haversine(longitude_t, latitude_t, longitude_p, latitude_p)

            new_miles = WithinMiles(state_fp=state_fp,
                                    county_fp=county_fp,
                                    tract_ce=tract_ce,
                                    population=population,
                                    latitude_t=latitude_t,
                                    longitude_t=longitude_t,
                                    object_id=object_id,
                                    latitude_p=latitude_p,
                                    longitude_p=longitude_p,
                                    city=city,
                                    state=state,
                                    zipcode=zipcode,
                                    miles=miles)
            create_obj.append(new_miles)
        session.add_all(create_obj)
        session.commit()
        count += 1


def delete_all():
    tracts = session.query(Tract).all()
    physicians = session.query(Physicians).all()
    miles = session.query(WithinMiles).all()
    print 'starting tracts'
    for tract in tracts:
        session.delete(tract)
    print 'starting physicians'
    for physician in physicians:
        session.delete(physician)
    print 'starting miles'
    for mile in miles:
        session.delete(mile)
    session.commit()

# [48.0, 1.0, 950401.0, 5422.0, 31.755614, -95.823901]
# [14178, -95.444343, 30.129775, 'SPRING', 'TX', 77380]
# 28.710983 -99.829416
# 31.99936,-95.53183
if __name__ == '__main__':
    # delete_all()
    # print haversine('-99.829416', '28.710983', '-95.53183', '31.99936')
    unpack_centroids()
    unpack_physicians()
    populate_distance_table()
    print 'All done'
