attempted_level = 13
point1 = (11, 852324)
point2 = (12, 1274800)
point3 = (14, 2393896)
m1 = (point2[1] - point1[1]) / (point2[0] - point1[0])
b1 = point2[1] - m1 * point2[0]
print("y = " + str(m1) + "x + " + str(b1))

m3 = (point3[1] - point2[1]) / (point3[0] - point2[0])
b3 = point3[1] - m3 * point3[0]
print("y = " + str(m3) + "x + " + str(b3))

# ans = (m1 + m2 + m3) * attempted_level / 3 + (b1 + b2 + b3) / 3
ans = (m1 + m3) * attempted_level / 2 + (b1 + b3) / 2
print(attempted_level, ans)
print((1741568 - ans)/1741568)
