# size is 39 x 36
import re
import os
import sys

iw = 39
ih = 36

with open('cssdesc.txt', 'r') as myfile:
    data = myfile.readlines()

data = [line.strip() for line in data]

wicons = {}

for line in data:
  elements = line.split(' ')
  if len(elements) > 2:
    x = int(re.findall(r'\d+', elements[-2])[0])
    del elements[-2]
    y = int(re.findall(r'\d+', elements[-1])[0])
    del elements[-1]
    for id in elements:
      id = re.sub(r'[^a-zA-Z0-9]', '', id)
      wicons[id] = [x, y]

for id in wicons:
  coords = wicons[id]
  cl = "convert wm.png -crop " + str(iw) + "x" + str(ih) + "+" + str(coords[0]) + "+" + str(coords[1]) + " " + id + ".png"
  os.system(cl)
