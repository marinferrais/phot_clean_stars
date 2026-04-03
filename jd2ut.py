#!/usr/bin/env python3

""" JD2UT - Convert julian in isot time

    creation : JUL 2021
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

# Numerical computing
#import numpy as np

# astropy Time package
from astropy.time import Time

#
# --- FUNCTIONS ---------------------------------------------------------------
#

def jd2ut(times):
    """

    Parameters
    ----------

    Returns
    -------

    """
    t = Time(times, format='jd')

    return t.isot

#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('times', help='list of julian days', nargs='+')

    args = parser.parse_args()

    times = sorted(args.times)

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #
    isot_list = jd2ut(times)

    for t,isot in zip(times, isot_list):
        print(f'> {t}   ->   {isot}')
