import pytest
from api.events import function1, Events

@pytest.fixture
def events_init():
    ''' Define initialization vals for the Events class '''
    init_vals = {
        "lat": 34.34,
        "lng": -119.123,
        "elevation": 2138,
        "reference_ambient": 10.0,
        "reference_pressure": 782.1,
    }
    return init_vals


def test_function1():
    assert function1(5) == 5

def test_sortTuple(events_init):
    tupleList = [ ("second", 2), ("first", 1) ]
    sortedTupleList = [ ("first", 1), ("second", 2) ]

    e = Events(**events_init)
    assert e._sortTuple(tupleList) == sortedTupleList