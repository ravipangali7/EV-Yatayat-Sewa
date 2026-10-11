from django.test import SimpleTestCase

from booking.views.trip_views import select_reached_stop_index


class _Place:
    def __init__(self, lat, lng):
        self.latitude = lat
        self.longitude = lng


class ReachedStopTests(SimpleTestCase):
    def test_picks_stop_on_the_far_side_of_the_road(self):
        # About 40m apart. The vehicle is beside the second pin, still inside
        # the first pin's circle. The second stop is the one to announce.
        first = _Place(27.7000, 85.3000)
        second = _Place(27.7003617, 85.3000)
        vehicle_lat, vehicle_lng = 27.7003617, 85.300152
        points = [
            ('stop', first, None),
            ('stop', second, None),
        ]
        index, crossed = select_reached_stop_index(points, vehicle_lat, vehicle_lng, 0.5)
        self.assertEqual(index, 1)
        self.assertTrue(crossed)

    def test_stays_on_the_stop_not_yet_crossed(self):
        first = _Place(27.7000, 85.3000)
        second = _Place(27.7003617, 85.3000)
        points = [
            ('stop', first, None),
            ('stop', second, None),
        ]
        index, crossed = select_reached_stop_index(points, 27.7000, 85.3000, 0.5)
        self.assertEqual(index, 0)
        self.assertTrue(crossed)

    def test_ignores_a_stop_far_ahead(self):
        here = _Place(27.7000, 85.3000)
        ahead = _Place(27.7180, 85.3000)
        points = [
            ('stop', here, None),
            ('stop', ahead, None),
        ]
        index, crossed = select_reached_stop_index(points, 27.7000, 85.3000, 0.5)
        self.assertEqual(index, 0)
        self.assertTrue(crossed)
