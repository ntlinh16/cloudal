from operator import ipow
import os
import pytest

from cloudal.utils import parse_config_file, is_ip

@pytest.mark.parametrize('file_path, message', [
    (None, 'Please enter the configuration file path'),
    ('', 'Please enter the configuration file path'),
    ('a/b/c', 'Please enter an existing configuration file path')
])
def test_parse_config_file_wrong_input(file_path, message):
    with pytest.raises(IOError) as exc_info:
        parse_config_file(file_path)
    assert message in str(exc_info)


def test_parse_config_file_valid_input():
    expected = {'walltime': 23400,
                'starttime': None,
                'cloud_provider_image': 'debian10-x64-big',
                'clusters': [{'cluster': 'dahu', 'n_nodes': 3}],
                'parameters': {'iteration': ['1..4'], 'duration': 10,'workloads': 'write' }}

    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "../test_data/test.yaml")
    result = parse_config_file(file_path)
    assert result == expected

@pytest.mark.parametrize('ip', [
    '',
    '   ',
    'a,b,c,d',
    'abcyz',
    'a.b.c',
    'a.a'
])
def test_is_ip_wrong_input(ip):
    actual = is_ip(ip)
    assert actual == False

@pytest.mark.parametrize('ip', [
    '1.2.3.0',
    '0.0.0.0',
    '255.255.255.255'
])
def test_is_ip(ip):
    actual = is_ip(ip)
    assert actual == True