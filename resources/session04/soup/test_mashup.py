import pytest

from mashup import result_generator, get_geojson, set_marker_color


def test_result_generator():
    result_list = []
    for result in result_generator('Average Score', True, 5):
        result_list.append(result)
    for i in range(len(result_list)-1):
        assert result_list[i]['Average Score'] >= result_list[i+1]['Average Score']
    assert len(result_list) == 5
    result_list = []
    for result in result_generator('High Score', False, 5):
        result_list.append(result)
    for i in range(len(result_list)-1):
        assert result_list[i]['High Score'] <= result_list[i+1]['High Score']
    assert len(result_list) == 5
    result_list = []
    for result in result_generator('Total Inspections', True, 1):
        result_list.append(result)
    assert len(result_list) == 1


def test_set_marker_color():
    # generate geojson result set
    total_result = {'type': 'FeatureCollection', 'features': []}
    for result in result_generator('Average Score', True, 10):
        geojson = get_geojson(result)
        total_result['features'].append(geojson)
    total_result['features'] = set_marker_color('Average Score', total_result['features'])
    # calculate avg. score of result set
    scores = [result['properties']['Average Score'] for result in total_result['features']]
    avg_score = sum(scores)/len(scores)
    # assert color values set according to score
    for i in range(len(total_result)-1):
        if total_result['features'][i]['properties']['Average Score'] >= (avg_score+5):
            assert total_result['features'][i]['properties']['marker-color'] == '#00ff00'
        elif total_result['features'][i]['properties']['Average Score'] <= (avg_score-5):
            assert total_result['features'][i]['properties']['marker-color'] == '#ff0000'
        else:
            assert total_result['features'][i]['properties']['marker-color'] == '#ffff00'


