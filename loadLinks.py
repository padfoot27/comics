from comics import db,Links

f = open('links.txt','r')

for i in range(3696):
    src = f.readline().split()[1]
    l = Links(src=src)

