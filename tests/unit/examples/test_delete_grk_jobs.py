import pytest

from examples.delete.delete_g5k_jobs import parse_job_ids

@pytest.mark.parametrize('job_ids', [
    '',
    '   ',
    'a,b,c,d',
    'abcyz',
    'a:b:c',
    'a:a'
])
def test_parse_job_ids_wrong_input(job_ids):
    with pytest.raises(ValueError) as exc_info:
        parse_job_ids(job_ids)
    assert 'Please give the right format of job IDs <site:id>,<site:id>....' in str(exc_info)


@pytest.mark.parametrize('job_ids, results', [
    ('a:1,b:2', [(1,'a'),(2,'b')]),
    ('a:1,', [(1,'a')]),
    ('a:1', [(1,'a')]),
])
def test_parse_job_ids_correct_input(job_ids, results):
    actual = parse_job_ids(job_ids)
    assert actual == results