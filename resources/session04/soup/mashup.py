import sys
from pprint import pprint  # used for debugging
from bs4 import BeautifulSoup
import geocoder
import json
import pathlib
import re
import requests
import click


INSPECTION_DOMAIN = 'http://info.kingcounty.gov'
INSPECTION_PATH = '/health/ehs/foodsafety/inspections/Results.aspx'
INSPECTION_PARAMS = {
    'Output': 'W',
    'Business_Name': '',
    'Business_Address': '',
    'Longitude': '',
    'Latitude': '',
    'City': '',
    'Zip_Code': '',
    'Inspection_Type': 'All',
    'Inspection_Start': '',
    'Inspection_End': '',
    'Inspection_Closed_Business': 'A',
    'Violation_Points': '',
    'Violation_Red_Points': '',
    'Violation_Descr': '',
    'Fuzzy_Search': 'N',
    'Sort': 'H'
}


def get_inspection_page(**kwargs):
    url = INSPECTION_DOMAIN + INSPECTION_PATH
    params = INSPECTION_PARAMS.copy()
    for key, val in kwargs.items():
        if key in INSPECTION_PARAMS:
            params[key] = val
    resp = requests.get(url, params=params)
    resp.raise_for_status()  # raise python exception based on http status
    return resp.text


def parse_source(html):
    parsed = BeautifulSoup(html)
    return parsed


def load_inspection_page(name):
    file_path = pathlib.Path(name)
    return file_path.read_text(encoding='utf8')


def restaurant_data_generator(html):
    id_finder = re.compile(r'PR[\d]+~')
    return html.find_all('div', id=id_finder)


def has_two_tds(elem):
    is_tr = elem.name == 'tr'
    td_children = elem.find_all('td', recursive=False)
    has_two = len(td_children) == 2
    return is_tr and has_two


def clean_data(td):
    return td.text.strip(" \n:-")


def extract_restaurant_metadata(elem):
    restaurant_data_rows = elem.find('tbody').find_all(
        has_two_tds, recursive=False
    )
    rdata = {}
    current_label = ''
    for data_row in restaurant_data_rows:
        key_cell, val_cell = data_row.find_all('td', recursive=False)
        new_label = clean_data(key_cell)
        current_label = new_label if new_label else current_label
        rdata.setdefault(current_label, []).append(clean_data(val_cell))
    return rdata


def is_inspection_data_row(elem):
    is_tr = elem.name == 'tr'
    if not is_tr:
        return False
    td_children = elem.find_all('td', recursive=False)
    has_four = len(td_children) == 4
    this_text = clean_data(td_children[0]).lower()
    contains_word = 'inspection' in this_text
    does_not_start = not this_text.startswith('inspection')
    return is_tr and has_four and contains_word and does_not_start


def get_score_data(elem):
    inspection_rows = elem.find_all(is_inspection_data_row)
    samples = len(inspection_rows)
    total = 0
    high_score = 0
    average = 0
    for row in inspection_rows:
        strval = clean_data(row.find_all('td')[2])
        try:
            intval = int(strval)
        except (ValueError, TypeError):
            samples -= 1
        else:
            total += intval
            high_score = intval if intval > high_score else high_score

    if samples:
        average = total/float(samples)
    data = {
        u'Average Score': average,
        u'High Score': high_score,
        u'Total Inspections': samples
    }
    return data


def result_generator(sort_by, low_to_high, count):
    use_params = {
        'Inspection_Start': '2/1/2013',
        'Inspection_End': '2/1/2015',
        'Zip_Code': '98101'
    }
    # html = get_inspection_page(**use_params)
    html = load_inspection_page('inspection_page.html')
    parsed = parse_source(html)
    content_col = parsed.find("td", id="contentcol")
    data_list = restaurant_data_generator(content_col)
    restaurant_list = []
    for data_div in data_list:
        metadata = extract_restaurant_metadata(data_div)
        inspection_data = get_score_data(data_div)
        metadata.update(inspection_data)
        restaurant_list.append(metadata)
    if sort_by:
        restaurant_list = sorted(restaurant_list,
                                 key=lambda k: k[sort_by],
                                 reverse=low_to_high)
    for restaurant in restaurant_list[:count]:
        yield restaurant


def get_geojson(result):
    address = " ".join(result.get('Address', ''))
    if not address:
        return None
    geocoded = geocoder.google(address)
    geojson = geocoded.geojson
    inspection_data = {}
    use_keys = (
        'marker-color',
        'Business Name',
        'Average Score',
        'Total Inspections',
        'High Score'
    )
    for key, val in result.items():
        if key not in use_keys:
            continue
        if isinstance(val, list):
            val = " ".join(val)
        inspection_data[key] = val
    geojson['properties'] = inspection_data
    return geojson


# functions for dealing with command line args
# def sort_order(args):
#     if 'reverse' not in args:
#         return True
#     else:
#         return False


# def sorter(args):
#     sort_by = {
#         'highscore': 'High Score',
#         'averagescore': 'Average Score',
#         'mostinspections': 'Total Inspections',
#     }
#     for order in sort_by:
#         if order in args:
#             return sort_by[order]


# def get_count(args):
#     for arg in args:
#         try:
#             arg = int(arg)
#             return arg
#         except ValueError:
#             continue
#     return 10


def set_marker_color(sort_by, results):
    # calculate the average score for this sample size and sorting criteria
    scores = [result['properties'][sort_by] for result in results]
    avg_score = sum(scores)/len(scores)
    # set marker-color property for results based on relationship to avg. score
    # green=go, yellow=proceed with caution, red=stop
    for result in results:
        if result['properties'][sort_by] >= (avg_score+5):
            result['properties']['marker-color'] = '#00ff00'
        elif result['properties'][sort_by] <= (avg_score-5):
            result['properties']['marker-color'] = '#ff0000'
        else:
            result['properties']['marker-color'] = '#ffff00'
    return results


@click.command()
@click.option('--sort-by',
              type=click.Choice(['Average Score', 'High Score', 'Total Inspections']),
              prompt=True,
              help='Sorting options: averagescore, highscore, mostinspections')
@click.option('--low-to-high', is_flag=True, default=True)
@click.option('--count', default=10, prompt=True)
def save_results(sort_by, low_to_high, count):
    total_result = {'type': 'FeatureCollection', 'features': []}
    # get command line arguments for sorting, limiting and ordering results
    # explore argparse or click for better command line interface
    # args = sys.argv[1:]
    # count = get_count(args)
    # sort_by = sorter(sort_by)
    # sort_order = sort_order(args)
    for result in result_generator(sort_by, low_to_high, count):
        geojson = get_geojson(result)
        total_result['features'].append(geojson)
    # set marker-color property for result set based on sorting criteria
    total_result['features'] = set_marker_color(sort_by, total_result['features'])
    with open('my_map.json', 'w') as fh:
        json.dump(total_result, fh)

if __name__ == '__main__':
    save_results()
    # total_result = {'type': 'FeatureCollection', 'features': []}
    # # get command line arguments for sorting, limiting and ordering results
    # # explore argparse or click for better command line interface
    # args = sys.argv[1:]
    # count = get_count(args)
    # sort_by = sort_by(args)
    # sort_order = sort_order(args)
    # for result in result_generator(count, sort_by, sort_order):
    #     geojson = get_geojson(result)
    #     total_result['features'].append(geojson)
    # # set marker-color property for result set based on sorting criteria
    # total_result['features'] = set_marker_color(sort_by, total_result['features'])
    # with open('my_map.json', 'w') as fh:
    #     json.dump(total_result, fh)
