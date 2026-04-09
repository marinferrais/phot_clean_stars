#!/usr/bin/env python3

""" GIF_LIGHTCURVE -

    creation : AUG 2025
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

import numpy as np
import matplotlib.pyplot as plt
import imageio
import io
from astropy.io import ascii
from astropy.time import Time
from astropy.table import join
from tqdm import tqdm
from pathlib import Path

#
# --- FUNCTIONS ---------------------------------------------------------------
#

def reject_outliers(data, nsig=3):
    # distance data to the median
    d = np.abs(data - np.median(data))
    # median distance
    mdev = np.median(d)
    # clipped data
    lower_bound = np.median(data) - nsig*mdev
    upper_bound = np.median(data) + nsig*mdev
    return data.clip(lower_bound, upper_bound)

def create_magnitude_gif(obsfiles, gifname='lightcurve.gif', delay=0.2, size=6):
    frames = []
    obs_list = []
    field_epoch = 'epoch'
    field_mag = 'mag'
    field_err = 'err_pho'

    for obsfile in obsfiles:
        obs = ascii.read(obsfile, format='rst')[field_epoch,field_mag,field_err]
        obs_list.append(obs)
    
    yliminf, ylimsup = [], []
    margin = 0.05
    for obs in obs_list:
        mag_clipped = reject_outliers(obs[field_mag])
        ylim = mag_clipped.min()-margin, mag_clipped.max()+margin
        yliminf.append(ylim[0])
        ylimsup.append(ylim[1])
    ylim = max(ylimsup), min(yliminf)
    
    if len(obs_list) > 1:
        obs = join(obs_list[0], obs_list[1], keys='epoch', join_type='outer')
    if len(obs_list) > 2: # more than 2 obs not working well atm
        for i in range(2, len(obs_list)):
            obs_list[i].rename_column(field_mag, f'{field_mag}_1')
            obs_list[i].rename_column(field_err, f'{field_err}_1')
            obs = join(obs, obs_list[i], keys='epoch', join_type='outer')

    labels = ['Original','Star removed']
    # single plot
    fig, ax = plt.subplots(figsize=(18,12))
    if len(obs_list) == 1:
        x, y, dy = obs[field_epoch], obs[field_mag], obs[field_err]
        ax.errorbar(x, y, yerr=dy, fmt='.', alpha=0.7)
    else:
        for j in range(len(obs_list)):
            x, y, dy = obs[field_epoch], obs[f'{field_mag}_{j+1}'], obs[f'{field_err}_{j+1}']
            ax.errorbar(x, y, yerr=dy, fmt='.', alpha=0.7, label=labels[j])
            ax.plot(x[y > ylim[0]], [ylim[0]] * len(x[y > ylim[0]]), 'v', markersize=5, color=f'C{j}', clip_on=False)
            ax.plot(x[y < ylim[1]], [ylim[1]] * len(x[y < ylim[1]]), '^', markersize=5, color=f'C{j}', clip_on=False)
    ax.invert_yaxis()
    ax.set_xlabel("Julian Date")
    ax.set_ylabel("Magnitude")
    ax.set_ylim(ylim)
    ax.legend()
    fig.tight_layout()
    plt.show()
    plotname = f"{Path(gifname).with_suffix('.png')}"
    print(f'> Saving single plot to {plotname}')
    plt.savefig(plotname, format='png')
    plt.close(fig)

    # Loop to highlight each point
    for i in tqdm(range(len(obs))):
        fig, ax = plt.subplots(figsize=(size,0.6*size))

        if len(obs_list) == 1:
            time_jd, mag, mag_err = obs[field_epoch], obs[field_mag], obs[field_err]
            ax.errorbar(time_jd, mag, yerr=mag_err, fmt='.', alpha=0.7)
            ax.plot(time_jd[i], mag[i], 'r.', zorder=10, label=f'{i}')
        else:
            for j in range(len(obs_list)):
                x, y, dy = obs[field_epoch], obs[f'{field_mag}_{j+1}'], obs[f'{field_err}_{j+1}']
                ax.errorbar(x, y, yerr=dy, fmt='.', alpha=0.7, label=labels[j]) # f'{Path(obsfiles[j]).name}'
                ax.plot(x[i], y[i], 'r+', markersize=7, zorder=100)
                ax.plot(x[y > ylim[0]], [ylim[0]] * len(x[y > ylim[0]]), 'v', markersize=5, color=f'C{j}', clip_on=False)
                ax.plot(x[y < ylim[1]], [ylim[1]] * len(x[y < ylim[1]]), '^', markersize=5, color=f'C{j}', clip_on=False)
                if y[i] > ylim[0]:
                    ax.plot(x[i], ylim[0], 'v', markersize=5, color='r', clip_on=False, zorder=20)
                elif y[i] < ylim[1]:
                    ax.plot(x[i], ylim[1], '^', markersize=5, color='r', clip_on=False, zorder=20)

        ax.invert_yaxis()
        ax.set_xlabel("Julian Date")
        ax.set_ylabel("Magnitude")
        ax.set_ylim(ylim)
        ax.set_title(f"{Time(x[i], format='jd').isot} : {i+1}")
        ax.legend()

        # Save frame to memory
        buf = io.BytesIO()
        fig.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        frames.append(imageio.v2.imread(buf))
        plt.close(fig)

    # Save to GIF
    imageio.mimsave(gifname, frames, fps=1/delay, loop=0, optimize=True)
    print(f"> Saving GIF to {gifname}")
#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('obsfiles', help='list of obs files', nargs='+')
    parser.add_argument("-dl", "--delay", help='delay between images (default=0.2s)',
                        default=0.2, type=float)
    parser.add_argument("-n", "--gifname", help='output gif name',
                        default='lightcurve.gif', type=str)
    parser.add_argument("-sz", "--size", help='Figure horizontal size',
                        default=6, type=float)

    args = parser.parse_args()

    obsfiles = sorted(args.obsfiles)
    dl = args.delay
    gifname = args.gifname
    size = args.size

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #
    create_magnitude_gif(obsfiles, gifname=gifname, delay=dl, size=size)
