#!/usr/bin/env python3

""" SCRIPT_TEMPLATE -

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

def ut2jd(times):
    """

    Parameters
    ----------

    Returns
    -------

    """

    for i, time in enumerate(times):
        # handle date format yyyymmdd
        if len(time) == 8:
            time = f'{time[:4]}-{time[4:6]}-{time[6:]}'
        # make sure time is indicated, not just date
        if len(time) == 10:
            times[i] = time + 'T20:00:00'
    t = Time(times, format='isot', scale='utc')

    return t.jd

#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('times', help='list of times in utc format', nargs='+')

    args = parser.parse_args()

    times = sorted(args.times)

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #
    jds = ut2jd(times)

    for t,jd in zip(times, jds):
        print(f'> {t}   ->   {jd}')
