import pytest

from uctl2_back.watched_property import WatchedProperty


def test_watched_property():
    p1 = WatchedProperty(1)

    assert p1.get_value() == 1
    p1.set_value(1)
    assert p1.get_value() == 1
    assert not p1.has_changed

    p1.set_value(2)
    assert p1.get_value() == 2
    assert p1.has_changed

    p2 = WatchedProperty()

    with pytest.raises(ValueError):
        p2.get_value()

    p2.set_value('test')
    assert p2.get_value() == 'test'
