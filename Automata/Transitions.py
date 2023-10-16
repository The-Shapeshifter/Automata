from math import exp, log
from States import States

NUM = 1
Cfnm = 0.010417
cfa = -0.00069
cfb = 258618.080
cfd = 4 // 4.3
cfm = 0.016 // 0.013
Cfp = 2
FrabT = 25
CfNFGT = 8.5
CfxNU = 0.135 // 0.4
CfxNFF = 22 // 22
Cfalpha = 0.9
Dfmax = 0.0515
KF = 15
LAIMAX = 5 // 5.5
St = 10
B = -0.3354
TL = 4
v1 = 0.9
v2 = 26
v3 = 0.084
v4 = 0.143
v5 = 0.0295
v6 = 23
v7 = 0.58
v8 = 555.6
v9 = 0.5
tmin = 10
tmax = 35
v10 = 0.18
v11 = 0.0032
v12 = 0.02
v13 = 0.75
v14 = 0.154
v15 = 0.0625
v17 = 0.682
v18 = 3.8016
Q10 = 1.4
LAI_h = 0
counter = 0
h = 1
solar_h = 1
N = 7
Nd = N
Bio = 0.280
Wf = 0
Wm = 0
Rm = 0
Pg = 0
Tm = 0
Tdm = 0


def lai(temp):
    return ((cfa * cfb + LAIMAX * pow((N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)), cfd)) /
            (cfb + pow((N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)), cfd)))


def top(temp, rad):
    return v1 * v2 + v3 * (1 - v4 * exp(v5 * (temp - v6))) * v7 * rad * v8


def bottom(temp, rad):
    return v1 * v2 + v3 * (1 - v4 * exp(v5 * (temp - v6))) * v7 * rad * v8 * exp(-v7 * lai(temp))


def min_pg(temp):
    return 1 / (1 + 9 * exp(-v9 * (temp - tmin)))


def max_pg(temp):
    return 1 - 1 / (1 + 9 * exp(-v9 * (temp - tmax)))


def bi():
    return max((v10 - v11 * Nd), v12)


def grnet(temp, rad):
    return v13 * ((Pg + min(min_pg(temp), max_pg(temp)) * ((v2 / v7) * log(top(temp, rad) / bottom(temp, rad)) * v17 * v18 / 24)) - (
            Rm + pow(Q10, (0.1 * temp - 2)) * cfm / 24) * (Bio - Wm)) * (1 - bi())


def d():
    return 1 - v14 * (Tdm - FrabT)


def c():
    return max(0.09, min(1.0, d()))


def e():
    return max(0.0, min(1.0, v15 * (Tm - CfNFGT)))


def g():
    return 0.0714 * (Tm - 9)


def f():
    return max(0.0, min(1.0, g()))


def states_transition(state, temp, rad):
    global N, Pg, Rm, Tm, Tdm, h, solar_h, counter, Bio, Nd, LAIMAX, LAI_h, KF, Wf, Wm

    match state:

        case States.S0:
            if h <= 23:
                N = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                Pg = Pg + min(min_pg(temp), max_pg(temp)) * ((v2 / v7) * log(top(temp, rad) / bottom(temp, rad)) * v17 * v18 / 24)
                Rm = Rm + pow(Q10, (0.1 * temp - 2)) * cfm / 24
                Tm = Tm * (h - 1) / h + temp / h
                Tdm = Tdm * solar_h / (solar_h + 1) + temp / (solar_h + 1)
                h = h + 1
                solar_h = solar_h + 1
                counter = counter + 1
                return state, N, Bio, LAI_h, Wf, Wm
            if h >= 23 and N < CfxNFF:
                N = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                counter = counter + 1
                Bio = Bio + grnet(temp, rad) - (
                        Cfp * (N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM) - Nd)
                        * min(1.0, max(0.0, lai(temp) - LAIMAX)))
                Nd = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                Pg = 0
                Rm = 0
                h = 1
                solar_h = 1
                LAI_h = lai(temp)
                return state, N, Bio, LAI_h, Wf, Wm
            if h >= 23 and N >= CfxNFF:
                N = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                counter = counter + 1
                Bio = (Bio + grnet(temp, rad) -
                       (Cfp * (N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM) - Nd) *
                        min(1.0, max(0.0, lai(temp) - LAIMAX))))
                Nd = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                Pg = 0
                Rm = 0
                h = 1
                solar_h = 1
                LAI_h = lai(temp)
                return States.S1, N, Bio, LAI_h, Wf, Wm

        case States.S1:
            if h <= 23:
                N = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                Pg = Pg + min(min_pg(temp), max_pg(temp)) * ((v2 / v7) * log(top(temp, rad) / bottom(temp, rad)) * v17 * v18 / 24)
                Rm = Rm + pow(Q10, (0.1 * temp - 2)) * cfm / 24
                Tm = Tm * (h - 1) / h + temp / h
                Tdm = Tdm * solar_h / (solar_h + 1) + temp / (solar_h + 1)
                h = h + 1
                solar_h = solar_h + 1
                counter = counter + 1
                return state, N, Bio, LAI_h, Wf, Wm
            if h >= 23 and N < CfxNFF + KF:
                N = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                counter = counter + 1
                Bio = Bio + grnet(temp, rad) - (
                        Cfp * (N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM) - Nd) *
                        min(1.0, max(0.0, lai(temp) - LAIMAX)))
                Wf = (Wf + Cfalpha * grnet(temp, rad) * (1 - exp(-CfxNU * (
                        N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM) - CfxNFF))) *
                      c() * e())
                Nd = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                Pg = 0
                Rm = 0
                h = 1
                solar_h = 1
                LAI_h = lai
                return state, N, Bio, LAI_h, Wf, Wm
            if h >= 23 and N >= CfxNFF + KF:
                N = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                counter = counter + 1
                Bio = Bio + grnet(temp, rad) - (
                        Cfp * (N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM) - Nd) *
                        min(1.0, max(0.0, lai(temp) - LAIMAX)))
                Wf = (Wf + Cfalpha * grnet(temp, rad) * (1 - exp(-CfxNU * (
                        N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM) - CfxNFF))) * c()
                      * e())
                Nd = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                Pg = 0
                Rm = 0
                h = 1
                solar_h = 1
                LAI_h = lai(temp)
                return States.S2, N, Bio, LAI_h, Wf, Wm

        case States.S2:
            if h < 23:
                N = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                Pg = Pg + min(min_pg(temp), max_pg(temp)) * ((v2 / v7) * log(top(temp, rad) / bottom(temp, rad))
                                                             * v17 * v18 / 24)
                Rm = Rm + pow(Q10, (0.1 * temp - 2)) * cfm / 24
                Tm = Tm * (h - 1) / h + temp / h
                Tdm = Tdm * solar_h / (solar_h + 1) + temp / (solar_h + 1)
                h = h + 1
                solar_h = solar_h + 1
                counter = counter + 1
                return state, N, Bio, LAI_h, Wf, Wm
            if h >= 23:
                N = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                counter = counter + 1
                Bio = Bio + grnet(temp, rad) - (
                        Cfp * (N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM) - Nd) *
                        min(1.0, max(0.0, lai(temp) - LAIMAX)))
                Wf = Wf + Cfalpha * grnet(temp, rad) * (1 - exp(-CfxNU * (
                        N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM) - CfxNFF))) * c() * e()
                Wm = Wm + Dfmax * (Wf - Wm) * f()
                Nd = N + Cfnm * min(min(0.25 + 0.025 * temp, 2.5 - 0.05 * temp), NUM)
                Pg = 0
                Rm = 0
                h = 1
                solar_h = 1
                LAI_h = lai(temp)
                return state, N, Bio, LAI_h, Wf, Wm
