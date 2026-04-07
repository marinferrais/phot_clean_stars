#!/usr/bin/env python3

"""  - TODO

    creation : JUL 2025
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

# astropy Table, Time
from astropy.table import Table, join
from astropy.time import Time

from pathlib import Path
import numpy as np

#
# --- FUNCTIONS ---------------------------------------------------------------
#

def combine_instru_zp(file_instru, file_zp, outfile='', targetname=None,
                      verbose=False):
    """ TODO
    """
    file_zp = Path(file_zp)
    
    if not targetname:
        targetname = str(file_zp.absolute().parent.name).split('_')[0]
    
    if not file_zp.exists():
        #file_zp = list(file_zp.parent.glob(f'photometry_*{targetname[:4]}_{targetname[4:]}_.dat'))[0]
        file_zp = list(file_zp.parent.glob(f'photometry_*_.dat'))[0]
        if not file_zp.exists():
            raise FileNotFoundError(f"[Errno 2] No such file or directory: {file_zp}")


    obs_code = {'TRAPPIST' : 'I40', 'ACP->NTM': 'Z53', 'Artemis':'Z25', 'ACP->Artemis':'Z25', 'Spacewatch_0.9-m_f/3_prime_focus':'691', 'RCOS':'W39'}
    obs_abrv = {'TRAPPIST' : 'TS', 'ACP->NTM': 'TN', 'Artemis':'SNO1', 'ACP->Artemis':'SNO1', 'Spacewatch_0.9-m_f/3_prime_focus':'SW09m', 'RCOS':'RO'}

    # Load PP photometry file with instrumental mags
    t_in = Table.read(file_instru, format='ascii.commented_header')
    t_in = t_in['filename', 'inst_mag', 'in_sig', '[9]']

    # Load original PP photometry file with correct ZP
    t_zp = Table.read(file_zp, format='ascii.commented_header')
    t_zp = t_zp['filename','julian_date', 'ZP', 'ZP_sig', '[5]', '[7]']
    if t_zp['ZP'][0] == 0.0:
        raise ValueError('ZP are zero -> check files input !')
    
    # Merge the two table on the filenames (only common columns) 
    t = join(t_in, t_zp)

    # Compute calibrated mag and absolute errors (ZP + instru mag)
    t['mag'] = t['ZP'] + t['inst_mag']
    t['err_abs'] = t['ZP_sig'] + t['in_sig']

    # Puting together the final table
    t.rename_column('julian_date', 'epoch')
    t.rename_column('in_sig', 'err_pho')
    t.rename_column('[7]', 'filter')
    t.rename_column('[5]', 'texp')
    t['band'] = t['filter']
    t['observatory'] = obs_code[t['[9]'][0]]
    t['targetname'] = targetname
    t['mag'].format = '%.4f'
    t['err_abs'].format = '%.4f'
    t = t['targetname', 'epoch', 'mag', 'err_abs', 'err_pho', 'filter', 'band', 'texp', 'observatory']

    t['err_abs'][np.where(t['mag'] > 100)] = 0.0
    t['mag'][np.where(t['mag'] > 100)] = 99.0 # avoid annoying fmt issues if some bad mags are > 100

    if verbose:
        t.pprint()

    if outfile == '':
        date = Time(int(t['epoch'][0])+0.3, format='jd').isot.split('T')[0]
        outfile = f"{targetname}_{obs_abrv[t_in['[9]'][0]]}_{date}_{t['band'][0]}.obs"
    print(f'> Saving table with calib mags to : {outfile}')
    t.write(outfile, format='ascii.rst', overwrite=True, comment=False)

    return t

#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="TODO")

    parser.add_argument('file_instru', 
                        help='PP photometric file with insrumental mags',
                        type=str)
    parser.add_argument('-zp','--file_zp',
                        help='PP photometric file with ZP', required=True,
                        type=str)
    parser.add_argument('-o','--outfile',
                        help='Name the the output obs file', required=None,
                        type=str, default='')
    parser.add_argument('-t','--target',
                        help='Target name', required=None,
                        type=str, default=None)
    parser.add_argument('-v','--verbose',
                        help='Verbose mode: print final table', 
                        action='store_true')
    args = parser.parse_args()

    file_instru = args.file_instru
    file_zp = args.file_zp
    outfile = args.outfile
    target = args.target
    verbose = args.verbose

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #
    combine_instru_zp(file_instru, file_zp, outfile=outfile, targetname=target,
                       verbose=verbose)