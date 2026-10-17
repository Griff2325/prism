import unittest
from prism_lights.core import Frame, Engine, Capabilities


def frame(color):
    return Frame.parse({'version':1,'width':1,'height':1,'pixels':[list(color)]})


class Fake:
    capabilities = Capabilities(power=True)
    def __init__(self):
        self.commands = []
        self.closed = False
    def color(self, rgb):
        self.commands.append(('color',rgb))
    def off(self):
        self.commands.append(('off',))
    def close(self):
        self.closed = True


class CoreTests(unittest.TestCase):
    def test_linear_average_and_zones(self):
        f = Frame.parse({'version':1,'width':3,'height':1,'pixels':[[255,0,0],[0,0,0],[0,0,255]]})
        self.assertEqual(f.sample('left'), (255,0,0))
        self.assertEqual(f.sample('right'), (0,0,255))
        self.assertEqual(f.sample('all'), (155,0,155))

    def test_frame_rejects_malformed_and_bounds(self):
        for data in ({}, {'version':True}, {'version':1,'width':128,'height':128,'pixels':[]},
                     {'version':1,'width':1,'height':1,'pixels':[[True,0,0]]},
                     {'version':1,'width':1,'height':1,'pixels':[[256,0,0]]}):
            with self.assertRaises(ValueError):
                Frame.parse(data)

    def test_rate_cap_smoothing_and_latest_frame(self):
        a = Fake(); e = Engine(a,hz=5,smoothing=.35,channel_cap=100)
        e.submit(frame((255,0,0)),0)
        e.tick(0)
        for i in range(1,101):
            e.submit(frame((0,0,255)),i/100)
            e.tick(i/100)
        self.assertLessEqual(len(a.commands),6)
        self.assertGreater(a.commands[-1][1][2],80)
        self.assertEqual(a.commands[-1][1][0],0)
        self.assertLessEqual(max(max(c[1]) for c in a.commands),100)

    def test_hold_stale_and_recovery(self):
        a=Fake();e=Engine(a,stale_seconds=.5)
        e.submit(frame((100,0,0)),0);e.tick(0);e.tick(.2)
        before=len(a.commands)
        e.tick(.5);e.tick(10)
        self.assertTrue(e.stale)
        self.assertEqual(len(a.commands),before)
        e.submit(frame((0,100,0)),10);e.tick(10.1)
        self.assertFalse(e.stale)
        self.assertGreater(len(a.commands),before)
        e.close();e.close()
        self.assertTrue(a.closed)
        self.assertNotIn(('off',),a.commands)

    def test_opt_in_off_once_on_stale(self):
        a=Fake();e=Engine(a,stale_seconds=.5,stale_policy='off')
        e.submit(frame((100,0,0)),0);e.tick(0);e.tick(.5);e.tick(1);e.close()
        self.assertEqual(a.commands.count(('off',)),1)

    def test_no_frames_no_commands(self):
        a=Fake();e=Engine(a,stale_policy='off');e.tick(20);e.close()
        self.assertEqual(a.commands,[])

    def test_invalid_policy_or_backwards_clock(self):
        for kwargs in ({'hz':100},{'stale_policy':'restore'},{'channel_cap':True}):
            with self.assertRaises(ValueError):Engine(Fake(),**kwargs)
        e=Engine(Fake());e.submit(frame((1,2,3)),2);e.tick(2)
        with self.assertRaises(ValueError):e.tick(1)
