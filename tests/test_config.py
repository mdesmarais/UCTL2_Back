import pytest
from datetime import datetime

from uctl2_back.config import Config, validate_bibs, validate_race_file, validate_route_file
from uctl2_back.exceptions import InvalidConfigError


def test_validate_bibs_should_RaiseInvalidConfigError_when_GivenNonUniqueBib():
    bibs = [1, 5, 3, 1, 9]

    with pytest.raises(InvalidConfigError):
        validate_bibs(bibs)


def test_validate_bibs_should_RaiseInvalidConfigError_when_GivenNegativeBib():
    with pytest.raises(InvalidConfigError):
        validate_bibs([0, 5, 7, 9])
    
    with pytest.raises(InvalidConfigError):
        validate_bibs([9, 6, 4, -6, 5])


def test_validate_bibs():
    validate_bibs([1, 2, 3, 4, 5])


def test_validate_race_file():
    pass


def test_validate_route_file_Should_RaiseInvalidConfigError_when_GivenNonGpxFile(tmp_path):
    route_file = tmp_path / 'uctl2.json'
    route_file.write_text('hello world')

    with pytest.raises(InvalidConfigError):
        validate_route_file(str(route_file))


def test_validate_route_file_Should_RaiseInvalidConfigError_when_GivenUnexistingFile(tmp_path):
    route_file = '%f.gpx' % (datetime.today().timestamp(), )

    with pytest.raises(InvalidConfigError):
        validate_route_file(route_file)


def test_validate_route_file(tmp_path):
    route_file = tmp_path / 'uctl2.gpx'
    route_file.write_text('hello world')

    validate_route_file(str(route_file))
