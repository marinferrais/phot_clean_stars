#!/usr/bin/env python3

""" FITS_ASTEROID - Identify an asteroid position on a given fits image

    creation : JUL 2023
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

# FITS manipulation
from astropy.wcs import WCS
from astropy.io import fits
from astropy.coordinates import SkyCoord

# Plotting
import matplotlib.pyplot as plt

# Horizons
from astroquery.jplhorizons import Horizons

from image_scaling import z_scale
from ut2jd import ut2jd
import rocks
from IAUcodes import tel2code

#
# --- FUNCTIONS ---------------------------------------------------------------
#

def get_eph(target, obs, jd, verbose=False): #TODO: put in toolbox
    """

    Parameters
    ----------

    Returns
    -------

    """
    # Parse target name
    target = rocks.id(target)[0]
    if verbose:
        print(target,obs,jd)
    obj = Horizons(id=target, location=obs, epochs=jd, id_type='smallbody')
    eph = obj.ephemerides()
    if verbose:
        print(eph)
    return eph


def telescop2IAU(telescope): #TODO: put in toolbox

    tele_translate = {'ACP->NTM':'TN', 'TRAP':'TS','TRAPPIST':'TS',
                      'SPECULOOS-EUROPA':'SPECU',
                      'SPECULOOS-IO':'SPECU',
                      'SPECULOOS-GANYMED':'SPECU',
                      'SPECULOOS-CALLISTO':'SPECU',
                      'ACP->Artemis':'SNO1',
                      'Artemis':'SNO1',
                      'C2PU/Omicron':'Omicron',
                      'Spacewatch-0.9m':'SW09m',
                      'Spacewatch 0.9-m f/3 prime focus':'SW09m',
                      'Robinson_Mono':'RO',
                      'Robinson':'RO',
                      }
    
    IAUlist = {'TN':'Z53', 'TS':'I40', 'MOSS':'J43', 'SSO2':'309', 'SNO1':'Z25',
           'DTC':'690', 'MO':'J43', 'BW':'U82', 'C2PU':'010', 'SPECU':'W75',
           'SW09m':'691', 'RO':'W39',
           }
    
    #return IAUlist[tele_translate[telescope]]
    return tel2code(tele_translate[telescope])

def fix_header(header):
    try:
        header['EQUINOX'] = float(header['EQUINOX'])
    except KeyError:
        print("Keyword 'EQUINOX' not found.")
    header['CTYPE1'] = 'RA---TPV'
    header['CTYPE2'] = 'DEC--TPV'
    for i in range(1,3):
        try:
            header[f'CRVAL{i}'] = float(header[f'CRVAL{i}'])
        except KeyError:
            print(f"Keyword 'CRVAL{i}' not found.")
        try:
            header[f'CRPIX{i}'] = float(header[f'CRPIX{i}'])
        except KeyError:
            print(f"Keyword 'CRPIX{i}' not found.")
        try:
            header[f'CD{i}_1'] = float(header[f'CD{i}_1'])
        except KeyError:
            print(f"Keyword 'CD{i}' not found.")
        try:
            header[f'CD{i}_2'] = float(header[f'CD{i}_2'])
        except KeyError:
            print(f"Keyword 'CD{i}_2' not found.")
        for j in range(17):
            try:
                header[f'PV{i}_{j}'] = float(header[f'PV{i}_{j}'])
                #print(f'PV{i}_{j}', header[f'PV{i}_{j}'])
            except KeyError:
                continue
    


    return header


def fix_pp_header(header):
    """
    """
    # Define all known prefixes to check
    wcs_prefixes = ('CRPIX', 'CRVAL', 'CDELT', 'CD', 'PC', 'PV', 'QV', 'CROTA', 'LATPOLE', 'LONPOLE')
    
    # Sanitize values in-place
    for key in list(header.keys()):
        if key.startswith(wcs_prefixes):
            val = header[key]
            if isinstance(val, str):
                try:
                    header[key] = float(val)
                except ValueError:
                    print(f"Skipping malformed WCS value: {key} = {val}")

    # filter out unsupported PVn_m keys
    for key in list(header.keys()):
        if key.startswith('PV'):
            del header[key]

    return header

def get_fits_infos(filename, target=None, observatory=None, jd=None, fix_hdr=True):
    hdul = fits.open(filename)[0]
    data = hdul.data
    header = hdul.header

    if fix_hdr:
        #header = fix_header(header)
        header = fix_pp_header(header)

    if not target:
        target = header['OBJECT']
    date = header['DATE-OBS']
    jd = ut2jd(date)

    if not observatory:
        try:
            observatory = telescop2IAU(header['TELESCOP'])
        except KeyError:
            observatory = telescop2IAU(header['TEL_KEYW'])
    
    infos = target, observatory, jd

    return data, header, infos

def plot_ast(data, wcs, x, y, target=None):
    """
    """

    figsize = (10, 10)
    color = 'C01'
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={'projection':wcs})

    ax.imshow(z_scale(data, c=0.05), origin='lower', cmap='Greys_r')
    
    ax.plot(x, y, '+', color=color)
    circle = plt.Circle((x, y), 8, color=color, fill=False)
    ax.add_patch(circle)

    if target:
        ax.text(x, y+15, str(target), color=color)

    #ax.coords.grid(True, color='white', ls='solid')
    #overlay = ax.get_coords_overlay('fk5')
    #overlay.grid(color='white', ls='dotted')

    fig.tight_layout()
    plt.show()

def get_astpx(data, fits_infos, wcs, centroid=False, display=False):

    # Get ephemerides
    target, observatory, jd = fits_infos
    eph = get_eph(target, observatory, jd)
    # Get x, y asteroid position from RA/DEC coordinates
    ra, dec = eph['RA'], eph['DEC']
    x, y = wcs.world_to_pixel(SkyCoord(ra=ra, dec=dec))
    x, y = x[0], y[0]

    if np.isnan(x) or np.isnan(y):
        print('DD')

    #print(f'{x:.2f} {y:.2f}')
    if centroid:
        from photutils.centroids import centroid_com
        mask = np.ones_like(data, dtype=bool)
        mask[int(y)-10:int(y)+10, int(x)-10:int(x)+10] = False
        #plt.imshow(np.ma.masked_array(data, mask), origin='lower')
        #plt.show()
        x, y = centroid_com(data, mask=mask)
        #print(f'{x:.2f} {y:.2f}')

    if display:
        plot_ast(data, wcs, x, y, target=target)

    return [ra.value[0], dec.value[0], x, y]

#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('filenames', help='list of file names', nargs='+')
    parser.add_argument('-t','--target',
                        help='Target number/name/designation',
                        type=str)
    parser.add_argument('-o','--observatory',
                        help='IAU observatory code',
                        type=str)
    parser.add_argument('-c','--centroid',
                        help='Use a centroid to get more accurate position',
                        action='store_true')
    parser.add_argument('-d','--display',
                        help='Display result',
                        action='store_true')
    parser.add_argument('-nw','--no_warnings',
                        help='Suppress Astropy warnings',
                        action='store_true')

    args = parser.parse_args()

    filenames = sorted(args.filenames)
    target = args.target
    observatory = args.observatory
    centroid = args.centroid
    display = args.display
    no_warnings = args.no_warnings

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #

    # matplotlib style
    try:
        plt.style.use('/home/ferrais/Dropbox/photCodes/bmh.mplstyle')
    except OSError:
        print('Custom matplotlib style file not found -> use default')

    if no_warnings:
        import warnings
        from astropy.utils.exceptions import AstropyWarning
        warnings.simplefilter('ignore', category=AstropyWarning)

    
    for filename in filenames:
        data, header, fits_infos = get_fits_infos(filename,
                                                  target=target,
                                                  observatory=observatory)
        wcs = WCS(header)
        ra, dec, x, y = get_astpx(data,
                                  fits_infos,
                                  wcs, 
                                  centroid=centroid,
                                  display=display)

        print(f'> ra, dec = {ra:.2f} {dec:.2f}')
        print(f'> x, y = {x:.2f} {y:.2f}')
        
