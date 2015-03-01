from math import radians, cos, sin, asin, sqrt

from models import Physicians, Tract, TractCode

import pandas as pd
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
# from sqlalchemy.sql.expression import func
# from sqlalchemy.sql import label
import requests

import config

engine = create_engine(config.DB_STRING)

Session = sessionmaker(bind=engine)


Session.configure(bind=engine)
session = Session()


def haversine_threshold(lon1, lat1, lon2, lat2, threshold, inc):
    """
    http://stackoverflow.com/questions/15736995/
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)

    Return 1 if within Threhsold; else return 0
    """
    lon1, lat1, lon2, lat2 = float(lon1), float(lat1), float(lon2), float(lat2)
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    distance_miles = 3956 * c
    resp = inc if distance_miles <= threshold else 0
    return int(resp)


def do_calc():
    start_time = datetime.utcnow()

    def get_docs_within10(row):
        base_lat, base_long = row['lat_long']

        count = -1
        for lat_long in docs_lat_long_list:
            lat2, long2 = lat_long
            count += haversine_threshold(
                base_long, base_lat,
                long2, lat2,
                threshold=10, inc=1)
        return count

    def get_tracts_within10(row):
        base_lat, base_long = row['lat_long']

        count = 0
        for lat_long_pop in tracts_lat_long_pop_list:
            lat2, long2, pop = lat_long_pop
            append = haversine_threshold(
                base_long, base_lat,
                long2, lat2,
                threshold=10, inc=pop)
            count += append
        return count

    def ratio_10(row):
        try:
            # return float(row.within10) / int(pop_tract)
            return float(row['docs_within10']) / float(row['tracts_within10'])
        except ZeroDivisionError:
            return 0

    def sum_ratio10(row):
        return docs.loc[docs['tract_code'] == row.tract_code].ratio10.sum()

    print 'starting do calc'
    tract_query = session.query(Tract).all()
    docs_query = session.query(Physicians).all()
    print 'query complete'

    tracts = pd.DataFrame([tract.return_pd_dict()
                          for tract in tract_query
                          if tract.return_pd_dict()])

    print 'tract df done'

    docs = pd.DataFrame([doc.return_pd_dict()
                        for doc in docs_query
                        if doc.return_pd_dict()])
    print 'docs df done'

    docs_lat_long_list = docs['lat_long'].tolist()
    tracts_lat_long_pop_list = tracts['lat_long_pop'].tolist()

    print 'all docs within 10'
    docs['docs_within10'] = docs.apply(get_docs_within10, axis=1)

    print 'all tracts within 10'
    docs['tracts_within10'] = docs.apply(get_tracts_within10, axis=1)

    print 'calc ratios'
    docs['ratio10'] = docs.apply(ratio_10, axis=1)

    print 'calc sum or ratios'
    tracts['sum_ratio'] = tracts.apply(sum_ratio10, axis=1)
    tracts.to_csv('tractstracts')
    docs.to_csv('docsdocsdocs')

    end_time = datetime.utcnow()

    total_seconds = (end_time - start_time).total_seconds()
    print 'Complete...{0} minutes & {1} seconds'.format(
        int(total_seconds / 60),
        int(total_seconds) % 60
    )


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


def get_tract_code_id(tract_code):
    try:
        atract_code = session.query(TractCode).filter_by(
            tract_code=tract_code).one()
        return_obj = atract_code.id
    except:
        new = TractCode(tract_code=tract_code)
        session.add(new)
        session.commit()
        return_obj = new.id
    finally:
        return return_obj


def get_physician_tract_codes():
    count = 0
    for doc in session.query(Physicians).all():
        print count
        errors = []
        count += 1

        url = ("http://data.fcc.gov/api/block/find?format=json&latitude={0}"
               "&longitude={1}&showall=false".format(doc.latitude_p,
                                                     doc.longitude_p))

        r = requests.get(url)
        if r.status_code != 200:
            print 'NOOOOOOOOOOOOOOOOO'

        try:
            tract_code = r.json()['Block']['FIPS'][:-4]
            doc.tract_code_id = get_tract_code_id(tract_code)
        except:
            print r.json()
            errors.append(r.json())

    session.commit()
    print 'errors are: '
    print errors
    print 'all done with api call'


if __name__ == '__main__':
    # delete_all()
    # print haversine('-99.829416', '28.710983', '-95.53183', '31.99936')
    # unpack_centroids()
    # unpack_physicians()
    # populate_distance_table()
    # a = session.query(Tract).limit(0).first()
    # print a.tract_code_id
    # populate_tract_code()
    # get_physician_tract_codes()
    do_calc()
    # calc_countss()
    # calc_ratio(10)
    # calc_ratio(15)
    # calc_ratio(10)
    # calc_ratio(45)
    # calc_ratio(60)
    # print session.query(Physicians).all()[0].docs_within
    # print session.query(Physicians).all()[0].tracts_within
