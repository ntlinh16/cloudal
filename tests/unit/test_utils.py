import os
import pytest

from cloudal.utils import parse_config_file

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
                'clusters': [{'cluster': 'dahu', 'n_nodes': 3}]}

    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "../test_data/test.yaml")
    result = parse_config_file(file_path)
    assert result == expected
