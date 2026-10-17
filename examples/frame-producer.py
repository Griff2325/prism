#!/usr/bin/env python3
"""Synthetic RGB zone input example; emits no captured video or private data."""
import json
import math
import time
for i in range(100):
    print(json.dumps({'version': 1, 'width': 3, 'height': 1,
                      'pixels': [[round(90+70*math.sin(i/10)),30,10],
                                 [30,70,100], [15,30,140]]}), flush=True)
    time.sleep(.1)
