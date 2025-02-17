import math

from scipy.stats import norm
目标置信度 = 0.62
目标偏差值 = 5
设置出货率 = 0.000001

def cacu(e, v):
    s = math.sqrt(v)
    v = norm.ppf(目标置信度)
    a = norm.ppf(1 - 设置出货率/2)
    n = ((v * 293 * s / 目标偏差值) ** 2) * (1 + a ** 2)
    print(n / 126)

cacu(2.059324288, 2.36351143)