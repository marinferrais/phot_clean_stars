#!/usr/bin/env python3

""" OBS_NIGHT_ID_UPDATE - Update the n coilumns of an obs table, 
                          usefull to keep 

    creation :
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

from astropy.io import ascii


#
# --- FUNCTIONS ---------------------------------------------------------------
#


def obs_night_id_update(obs):
    """
    TODO
    Parameters
    ----------

    Returns
    -------

    """
     
    n = 1
    nc = obs['n'][0]
    for i, ni in enumerate(obs['n']):
        if ni != nc:
            n += 1
            nc = ni
        obs['n'][i] = n
            

    return obs


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
    jd_c, observatory_c, filter_c, band_c = 0, '', '', ''
    for row in obs:
        #jd, observatory, filter, band = int(row['epoch']), row['observatory'], row['filter'], row['band']
        jd, observatory, filter, band = float(row['epoch']), row['observatory'], row['filter'], row['band']
        if (jd-jd_c) > 0.4 or observatory != observatory_c or filter != filter_c or band != band_c:
            n += 1
            jd_c, observatory_c, filter_c, band_c = jd, observatory, filter, band
        n_list.append(n)
    obs.add_column(n_list, name='n', index=0)
    return obs


#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('filename', help='Photometry file names')
    parser.add_argument('-fr','--force_replace',
                        help='Force replace n column if it already exists',
                        action='store_true')

    args = parser.parse_args()

    fname = args.filename
    force_replace = args.force_replace



    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #
    
    obs = ascii.read(fname, format='rst')
    if 'n' not in obs.columns:
        obs = nights_id(obs)
    elif force_replace:
        print('> Force replacing n column')
        obs.remove_column('n')
        obs = nights_id(obs)
    else:
        obs = obs_night_id_update(obs)
    print(f'\n> Saving obs to {fname}')
    obs.write(fname, format='ascii.rst', overwrite=True, comment=False)



    

