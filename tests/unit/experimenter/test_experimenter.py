import os 

import pytest

from cloudal.experimenter import define_parameters
from cloudal.utils import parse_config_file

@pytest.mark.parametrize('parameters', [
    None,
    list(),
])
def test_define_parameters_wrong_input(parameters):
    with pytest.raises(TypeError) as exc_info:
        define_parameters(parameters)
    assert 'Parameters has to be a dictionary.' in str(exc_info)


def test_define_parameters():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "../../test_data/test.yaml")
    result = parse_config_file(file_path)
    actual = define_parameters(result['parameters'])
    # assert result is None
    assert isinstance(actual, dict)
    assert actual['iteration'] == range(1,5)
    assert actual['duration'] == [10]
    assert actual['workloads'] == ['write']
