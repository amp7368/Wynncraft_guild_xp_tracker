import time
from json import dumps

xp = list()
now = time.time()
for i in (range(10000)):
    xps = now - 60*60*24*20 + 60*60*24*i
    # print(xps)
    entry = {"type":"leader","date":xps,"level": 52, "xp":i*50000000}
    xp.append(entry)
a = {"Avicia": {"xp": xp, "time": 10, "channel":606941926058491906}}
with open("data.txt", 'w') as f:
    f.write(dumps(a))
print("done")