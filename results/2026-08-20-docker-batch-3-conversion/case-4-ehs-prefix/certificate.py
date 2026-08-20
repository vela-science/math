import math


def factor(n):
    fs = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            e = 0
            while n % d == 0:
                n //= d
                e += 1
            fs.append((d, e))
        d = 3 if d == 2 else d + 2
    if n > 1:
        fs.append((n, 1))
    return fs


members = []
for m in range(18):
    n = math.factorial(m) + 1
    fs = factor(n)
    witnesses = [p for p, e in fs if m >= 1 and p % m != 1 % m]
    is_member = m >= 1 and bool(witnesses)
    if is_member:
        members.append(m)
    residues = [(p, p % m if m else None) for p, e in fs]
    print(
        f"m={m}; factorial_plus_one={n}; prime_factorization="
        + "*".join(f"{p}^{e}" for p, e in fs)
        + f"; residues_mod_m={residues}; EHS={is_member}; "
        + f"witness={witnesses[0] if witnesses else None}"
    )
print("EHS_in_0_through_17=", members)
print("first_seven=", members[:7])
assert members[:7] == [8, 9, 13, 14, 15, 16, 17]
