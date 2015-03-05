from math import log
import pandas as pd


def get_theil_entropy(values):
    total = sum(values)
    entropy = 0

    for value in values:
        try:
            p = float(value) / total
            entropy += p * log(1 / p)
        except ZeroDivisionError:
            entropy = 0
    return entropy


def contrib_h_index(tract_pop, block_pop, tract_entropy, block_entropy):
    numerator = float(block_pop) * (tract_entropy - block_entropy)
    denominator = float(tract_pop) * tract_entropy
    return numerator / denominator


def calc_index():
    def calc_other_pop(row):
        return (row['total_pop'] - row['white_pop'] -
                row['black_pop'] - row['hispanic_pop'])

    def calc_h_index(row):
        return contrib_h_index(
            row['tract_total_pop'],
            row['total_pop'],
            row['tract_entropy'],
            row['block_entropy']
        )

    def block_entropy(row):
        white_pop = row['white_pop']
        black_pop = row['black_pop']
        hispanic_pop = row['hispanic_pop']
        other_pop = row['other_pop']
        return get_theil_entropy([white_pop, black_pop,
                                  hispanic_pop, other_pop])

    def tract_entropy(row):
        sub_df_sum = df[(df.tract == row['tract'])].sum()

        white_pop = sub_df_sum.white_pop
        black_pop = sub_df_sum.black_pop
        hispanic_pop = sub_df_sum.hispanic_pop
        other_pop = sub_df_sum.other_pop
        return get_theil_entropy([white_pop, black_pop,
                                  hispanic_pop, other_pop])

    def calc_tract_pop(row):
        return df[(df.tract == row['tract'])].sum().total_pop

    def calc_cumm_index(row):
        return df[(df.tract == row['tract'])].sum().h_theil_index

    # turn pop fields to int
    df = pd.read_csv('block_trim2.csv')
    df[['total_pop', 'black_pop', 'white_pop', 'hispanic_pop']] = df[['total_pop', 'black_pop', 'white_pop', 'hispanic_pop']].astype(int)
    df['other_pop'] = df.apply(calc_other_pop, axis=1)
    df['tract_pop'] = df.apply(calc_tract_pop, axis=1)
    df['block_entropy'] = df.apply(block_entropy, axis=1)
    df['tract_entropy'] = df.apply(tract_entropy, axis=1)
    df['tract_total_pop'] = df.apply(calc_tract_pop, axis=1)
    df['h_theil_index'] = df.apply(calc_h_index, axis=1)
    df['tract_cumm_index'] = df.apply(calc_cumm_index, axis=1)

    df.to_csv('final_h_index2.csv')


def open_csv():
    the_dicts = []
    with open('block.csv', 'r') as f:
        count = 0
        for line in f:
            list_line = line.split(',')
            list_line = [item.replace('"', '') for item in list_line]
            if count == 0:
                index_state = list_line.index('STATE')
                index_county = list_line.index('COUNTYSC')
                index_tract = list_line.index('TRACT')
                index_block = list_line.index('BLKGRP')
                index_total_pop = list_line.index('P0050001')
                index_white_pop = list_line.index('P0050003')
                index_black_pop = list_line.index('P0050004')
                index_hispanics_pop = list_line.index('P0050010')
                index_geo_id = list_line.index('GEOID10')
            else:
                if list_line[index_state] == '48':
                    the_dict = {
                        'state': list_line[index_state],
                        'county': list_line[index_county],
                        'tract': list_line[index_tract],
                        'block': list_line[index_block],
                        'total_pop': list_line[index_total_pop],
                        'white_pop': list_line[index_white_pop],
                        'black_pop': list_line[index_black_pop],
                        'hispanic_pop': list_line[index_hispanics_pop],
                        'index_geo_id': list_line[index_geo_id]
                    }
                    the_dicts.append(the_dict)
                if count % 20000 == 0:
                    print count
            count += 1
    df = pd.DataFrame(the_dicts)
    df.to_csv('block_trim2.csv')

open_csv()
print 'csv mini created'
calc_index()
print 'done'
