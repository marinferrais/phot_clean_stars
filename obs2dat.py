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
import numpy as np

# Filesytem paths
from pathlib import Path

# Astropy Time + io ascii
from astropy.time import Time
from astropy.io import ascii

# Horizons query
from astroquery.jplhorizons import Horizons

from IAUcodes import tel2code

#
# --- FUNCTIONS ---------------------------------------------------------------
#

def nights_id(obs):
    """
    TODO
    Parameters
    ----------

    Returns
    -------

    """
    n_list = []
    n = 0
    jd_c, observatory_c, filter_c, band_c = '', '', '', ''
    for row in obs:
        jd, observatory, filter, band = int(row['epoch']), row['observatory'], row['filter'], row['band']
        if jd != jd_c or observatory != observatory_c or filter != filter_c or band != band_c:
            n += 1
            jd_c, observatory_c, filter_c, band_c = jd, observatory, filter, band
        n_list.append(n)
    obs['n'] = n_list
    return obs

def obs2dat(obsfile,
            field_epoch='epoch', field_mag='mag', field_err='err_pho',
            save=False, write_header=False):
    """

    Parameters
    ----------

    Returns
    -------

    """
    obs = ascii.read(obsfile, format='rst')

    # add a column 'n' to numbers each nights
    if 'n' not in obs.columns:
        obs = nights_id(obs)

    data = np.array(obs[[field_epoch, field_mag, field_err]])
    data = np.array([obs[field_epoch], obs[field_mag], obs[field_err]]).T

    lList = []
    nights = []
    # Loop on each data blocks
    for i in range(1, obs['n'].max()+1):
        obs_i = obs[obs['n'] == i]
        lList.append(len(obs_i))
        filter = obs_i['filter'][0]
        mpccode = obs_i['observatory'][0]
        tel = tel2code((mpccode), invert=True)

        date = int(obs_i['epoch'][0]) + 0.4
        date = Time(date, format='jd').isot
        date = date.split('T')[0]
        date = date.replace('-', '')
        
        nights.append(f"{filter}{date}{tel}")
    
    if save:
        outfile = obsfile.with_suffix('.dat')
        print(f'> Saving to file: {outfile}')
        np.savetxt(outfile, data, fmt=['%10.6f','%10.5f','%.5f'])
    
    print(f"lList = {lList}")
    print(f"nights = {nights}")
    
    return data, lList, nights

def TBD(obsfile,
            field_epoch='epoch', field_mag='mag', field_err='err_pho',
            save=False):
    """

    Parameters
    ----------

    Returns
    -------

    """
    obs = ascii.read(obsfile, format='rst')

    # add a column 'n' to numbers each nights
    if 'n' not in obs.columns:
        obs = nights_id(obs)

    data = np.array(obs[[field_epoch, field_mag, field_err]])

    lList = []
    nights = []
    r, delta, alpha = [], [], []
    # Loop on each data blocks
    for i in range(1, obs['n'].max()+1):
        obs_i = obs[obs['n'] == i]
        lList.append(len(obs_i))
        filter = obs_i['band'][0]
        mpccode = obs_i['observatory'][0]
        tel = tel2code(mpccode, invert=True)

        date = int(obs_i['epoch'][0]) + 0.4
        date = Time(date, format='jd').isot
        date = date.split('T')[0]
        date = date.replace('-', '')
        
        nights.append(f"{filter}{date}{tel}")

        midTime = (obs_i['epoch'][0] + obs_i['epoch'][-1]) / 2.
        obj = Horizons(id=obs_i['targetname'], location=mpccode,
                       epochs=midTime)
        eph = obj.ephemerides()
        r = np.append(r, np.full((1, li), eph['r']))
        delta = np.append(delta, np.full((1, li), eph['delta']))
        alpha = np.append(alpha, np.full((1, li), eph['alpha_true']))
    
    if save:
        outfile = obsfile.with_suffix('.dat')
        print(f'> Saving to file: {outfile}')
        np.savetxt(outfile, data, fmt=['%10.6f','%10.5f','%.5f'])
    
    print(f"lList = {lList}")
    print(f"nights = {nights}")
    
    return

#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('obsfile', help='Astropy table file name')
    parser.add_argument('-fe', '--field_err', help='Mag errors field',
                        type=str, default='err_pho')
    parser.add_argument('-s','--save',
                        help='save to file',
                        action='store_true')
    parser.add_argument('-wh','--write_header',
                        help='Add header (final format)',
                        action='store_true')


    args = parser.parse_args()

    obsfile = Path(args.obsfile)
    field_err = args.field_err
    save = args.save
    write_header = args.write_header

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #
    obs2dat(obsfile, field_err=field_err, save=save, write_header=write_header)
