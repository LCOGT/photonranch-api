import ephem
import requests
import json
mars = ephem.Mars()
mars.compute('2008/1/1')
print(mars.ra)
print(mars.dec)

url = "https://api.photonranch.org/test/testephem"
url = "https://api.photonranch.org/test/testskyfield"
#print(requests.post(url).json())

from skyfield.api import load

planets = load('de421.bsp')
earth, mars = planets['earth'], planets['mars']

ts = load.timescale(builtin=True)
t = ts.now()
position = earth.at(t).observe(mars)
ra, dec, distance = position.radec()

print(str(ra))
print((dec))
print((distance))
print(json.dumps([str(ra), str(distance)]))