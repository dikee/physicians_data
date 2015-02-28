from math import radians, cos, sin, asin, sqrt

from models import Physicians, Tract, WithinMiles, TractCode

import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.sql.expression import func
from sqlalchemy.sql import label
import requests


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
    print session.query(Tract).delete()
    print session.query(Physicians).delete()
    #tracts = session.query(Tract).all()
    #physicians = session.query(Physicians).all()
    #miles = session.query(WithinMiles).all()
    #print 'starting tracts'
    #for tract in tracts:
    #    session.delete(tract)
    #print 'starting physicians'
    #for physician in physicians:
    #    session.delete(physician)
    #print 'starting miles'
    #for mile in miles:
    #    session.delete(mile)
    session.commit()


def _six_digits(value):
    value = str(int(value))
    while len(value) < 6:
        value = '0' + value
    return value


def get_tract_code_id(tract_code):
    try:
        atract_code = session.query(TractCode).filter_by(tract_code=tract_code).one()
        return_obj = atract_code.id
    except:
        new = TractCode(tract_code=tract_code)
        session.add(new)
        session.commit()
        return_obj = new.id
    finally:
        return return_obj


def populate_tract_code():
    count = 0
    tracts = session.query(Tract).all()
    for tract in tracts:
        print count
        count += 1 
        tract_code = tract.state_fp + tract.county_fp + tract.tract_ce
        tract.tract_code_id = get_tract_code_id(tract_code)    
    session.commit()

def get_physician_tract_codes():
    count = 0
    for doc in session.query(Physicians).all():
        print count
        errors = []
        count += 1
        url = "http://data.fcc.gov/api/block/find?format=json&latitude=%s&longitude=%s&showall=false" % (doc.latitude_p, doc.longitude_p)
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
    print errors
    print 'all done with api call' 


def calc_counts(threshold=30):
    docs =  session.query(Physicians).all()
    tracts = session.query(Tract).all()
    count = 0

    for doc in docs:
        doc_count = 0
        tract_count = 0
        lat = doc.latitude_p
        lon = doc.longitude_p
        
        for adoc in docs:
            if haversine(lon, lat, adoc.longitude_p, adoc.latitude_p) <= threshold:
                doc_count += 1
        doc.docs_within = doc_count

        for tract in tracts:
            if haversine(lon, lat, tract.longitude_t, tract.latitude_t) <= threshold:
                tract_count += 1
        doc.tracts_within = tract_count
        session.commit()
        print count
        count += 1
    print 'done with calc counts'


def calc_countss():
    docs =  session.query(Physicians).all()
    tracts = session.query(Tract).all()
    count = 0

    for doc in docs:
        doc_count_10 = 0
        doc_count_15 = 0
        doc_count_45 = 0
        doc_count_60 = 0

        tract_count_10 = 0
        tract_count_15 = 0
        tract_count_45 = 0
        tract_count_60 = 0

        lat = doc.latitude_p
        lon = doc.longitude_p

        for adoc in docs:
            if haversine(lon, lat, adoc.longitude_p, adoc.latitude_p) <= 10:
                doc_count_10 += 1

            if haversine(lon, lat, adoc.longitude_p, adoc.latitude_p) <= 15:
                doc_count_15 += 1

            if haversine(lon, lat, adoc.longitude_p, adoc.latitude_p) <= 45:
                doc_count_45 += 1

            if haversine(lon, lat, adoc.longitude_p, adoc.latitude_p) <= 60:
                doc_count_60 += 1

        doc.docs_within_10 = doc_count_10
        doc.docs_within_15 = doc_count_15
        doc.docs_within_45 = doc_count_45
        doc.docs_within_60 = doc_count_60

        for tract in tracts:
            if haversine(lon, lat, tract.longitude_t, tract.latitude_t) <= 10:
                tract_count_10 += 1

            if haversine(lon, lat, tract.longitude_t, tract.latitude_t) <= 15:
                tract_count_15 += 1

            if haversine(lon, lat, tract.longitude_t, tract.latitude_t) <= 45:
                tract_count_45 += 1

            if haversine(lon, lat, tract.longitude_t, tract.latitude_t) <= 60:
                tract_count_60 += 1

        doc.tracts_within_10 = tract_count_10
        doc.tracts_within_15 = tract_count_15
        doc.tracts_within_45 = tract_count_45
	doc.tracts_within_60 = tract_count_60

        session.commit()
        print count
        count += 1
    print 'done with calc counts'

def calc_ratio(distance):
    attr_map = {
	10: ['docs_within_10', 'tracts_within_10', 'ratio_10'],
	15: ['docs_within_15', 'tracts_within_15', 'ratio_15'],
        30: ['docs_within', 'tracts_within', 'ratio_30'],
	45: ['docs_within_45', 'tracts_within_45', 'ratio_45'],
	60: ['docs_within_60', 'tracts_within_60', 'ratio_60']
	}

    docs = session.query(Physicians).all()

    calc = attr_map[distance]
    count = 0
    for doc in docs:
        sum_physicians = getattr(doc, calc[0])
        #sum_pop = session.query(func.sum(WithinMiles.population)).filter(WithinMiles.miles<=distance, WithinMiles.object_id==doc.object_id)
        #sum_pop = session.query(WithinMiles, label('sum', func.sum(WithinMiles.population)), label('count', func.count(WithinMiles.id))).filter(WithinMiles.miles<=distance, WithinMiles.object_id==doc.object_id).all()
        #sum_pop = session.query(func.sum(WithinMiles.population).label('sum_pop')).filter(WithinMiles.miles<=distance, WithinMiles.object_id==doc.object_id)
        all = session.query(WithinMiles).filter(WithinMiles.miles<=distance, WithinMiles.object_id==doc.object_id)
        sum_pop = sum(int(a.population) for a in all)
        
        if sum_pop > 0:
            ratio = float(sum_physicians) / float(sum_pop)
        else:
            ratio = 0
        setattr(doc, calc[2], ratio)
	print "count(%s): %s    ratio: %s" % (distance, count, ratio)
        count += 1
    session.commit()


        #print dir(sum_pop)
        #print sum_pop.execute()
        #return
        #ratio = sum_physicians / sum_pop
        #setattr(doc, calc[2], ratio)
        #print sum_physicians, sum_pop, ratio
        #count = session.query(WithinMiles).filter(WithinMiles.miles<=distance, WithinMiles.object_id==doc.object_id).count()
        #print '------'
        #print count, getattr(doc, calc[1])
        #return

# [48.0, 1.0, 950401.0, 5422.0, 31.755614, -95.823901]
# [14178, -95.444343, 30.129775, 'SPRING', 'TX', 77380]
# 28.710983 -99.829416
# 31.99936,-95.53183
if __name__ == '__main__':
    #delete_all()
    #print haversine('-99.829416', '28.710983', '-95.53183', '31.99936')
    #unpack_centroids()
    #unpack_physicians()
    #populate_distance_table()
    #a = session.query(Tract).limit(0).first()
    #print a.tract_code_id
    #populate_tract_code()
    #get_physician_tract_codes()
    #calc_countss()
    calc_ratio(30)
    calc_ratio(15)
    calc_ratio(10)
    calc_ratio(45)
    calc_ratio(60)
    #print session.query(Physicians).all()[0].docs_within
    #print session.query(Physicians).all()[0].tracts_within
