#!/usr/bin/env python3

from astropy.coordinates import SkyCoord
from astropy.wcs import WCS

from PIL import Image, ImageDraw, ImageSequence, ImageFont
import io
from jd2ut import jd2ut
from skimage.transform import resize
from tqdm import tqdm
import numpy as np
import argparse
import os
import matplotlib.pyplot as plt
from pathlib import Path

from fits_asteroid import get_fits_infos, get_astpx
from fits_cropping import cropping
from fits_bkgsub import bkgsub_array
from image_scaling import z_scale, minmax_scale, manual_scale
#from parse_name import parse_name
import rocks


def folder_exist(folder):
    """Check if folder exist, if not it is created.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f'> New directory : {folder}')




def find_outlier_pixels(data, tolerance=3, display=False):
    """
    This function finds the hot or dead pixels in a 2D dataset. 
    Rolerance is the number of standard deviations used to cutoff the hot pixels
    The function returns a list of hot pixels and also an image with hot pixels removed
    From : https://stackoverflow.com/questions/18951500/automatically-remove-hot-dead-pixels-from-an-image-in-python
    """

    from scipy.ndimage import median_filter
    blurred = median_filter(data, size=2)
    difference = data - blurred
    threshold = tolerance*np.std(difference)

    #find the hot pixels, but ignore the edges
    hot_pixels = np.nonzero((np.abs(difference[1:-1,1:-1])>threshold) )
    hot_pixels = np.array(hot_pixels) + 1 #because we ignored the first row and first column

    fixed_image = np.copy(data) #This is the image with the hot pixels removed
    for y,x in zip(hot_pixels[0],hot_pixels[1]):
        fixed_image[y,x]=blurred[y,x]
    
    if display:
        plt.figure(figsize=(30,15))
        ax1 = plt.subplot(121)
        ax2 = plt.subplot(122)
        ax1.set_title('Raw data with hot pixels')
        ax1.imshow(z_scale(data,c=0.02),interpolation='nearest',origin='lower',cmap='Greys_r')
        for y,x in zip(hot_pixels[0],hot_pixels[1]):
            ax1.plot(x,y,'ro',mfc='none',mec='r',ms=10)

        ax2.set_title('Image with hot pixels removed')
        ax2.imshow(z_scale(fixed_image,c=0.02),interpolation='nearest',origin='lower',cmap='Greys_r')
        plt.show()
    
    return hot_pixels,fixed_image


def arrowedLine(draw, ptA, ptB, width=1, color=(0,255,0)):
    """
    Draw line from ptA to ptB with arrowhead at ptB. From :
    https://stackoverflow.com/questions/63671018/how-can-i-draw-an-arrow-using-pil
    """
    # Draw the line without arrows
    draw.line((ptA,ptB), width=width, fill=color)

    # Now work out the arrowhead
    # = it will be a triangle with one vertex at ptB
    # - it will start at 95% of the length of the line
    # - it will extend 8 pixels either side of the line
    x0, y0 = ptA
    x1, y1 = ptB
    arr_width = 0.1 * np.sqrt((x0-x1)**2 + (y0-y1)**2)
    #print(arr_width)
    arr_perc = 0.66
    # Now we can work out the x,y coordinates of the bottom of the arrowhead triangle
    xb = arr_perc*(x1-x0)+x0
    yb = arr_perc*(y1-y0)+y0

    # Work out the other two vertices of the triangle
    # Check if line is vertical
    if x0==x1:
       vtx0 = (xb-arr_width, yb)
       vtx1 = (xb+arr_width, yb)
    # Check if line is horizontal
    elif y0==y1:
       vtx0 = (xb, yb+arr_width)
       vtx1 = (xb, yb-arr_width)
    else:
       alpha = np.arctan2(y1-y0,x1-x0)-90*np.pi/180
       a = arr_width*2*np.cos(alpha)
       b = arr_width*2*np.sin(alpha)
       vtx0 = (xb+a, yb+b)
       vtx1 = (xb-a, yb-b)

    #draw.point((xb,yb), fill=(255,0,0))    # DEBUG: draw point of base in red - comment out draw.polygon() below if using this line
    #im.save('DEBUG-base.png')              # DEBUG: save

    # Now draw the arrowhead triangle
    draw.polygon([vtx0, vtx1, ptB], fill=color)
    #return im


def gif_text(gif_path, fits_infos_list, pos=None,
             target_width_ratio = 0.4,
             font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):

    im = Image.open(gif_path)

    # get infos to be written on the gif
    target = fits_infos_list[0][0]
    if target == '0003I' or target == 'A11pl3z':
        target = '3I/ATLAS'
    else:
        rocksid = rocks.id(target)
        if np.isnan(rocksid[1]):
            target = rocksid[0]
        else:
            target = f"({rocksid[1]}) {rocksid[0]}"

    code2name = {'I40': 'TRAPPIST-South', 'Z53': 'TRAPPIST-North',
                 'Z25': 'Artemis', '691':'Spacewatch-0.9m',
                 'W39':'Robinson Observatory',
                 }
    telescope = code2name.get(fits_infos_list[0][1], fits_infos_list[0][1])

    date = np.array(fits_infos_list)[:,2]
    n = len(date)
    date = jd2ut([float(jd) for jd in date])
    # uncomment below to have only date and no time
    #date = jd2ut([int(float(jd)) for jd in date])
    #date = [d.split('T')[0] for d in date]

    # Start with a guess font size
    font_size = 5
    font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(ImageSequence.Iterator(im)[0])
    text=date[0]
    img_width, img_height = ImageSequence.Iterator(im)[0].size
    # Increase font size until text is about target_width_ratio of the image width
    while True:
        text_width  = draw.textlength(text, font=font)
        if text_width >= target_width_ratio * img_width:
            break
        font_size += 1
        font = ImageFont.truetype(font_path, font_size)
    font2 = ImageFont.truetype(font_path, size=int(1.15*font_size))

    # A list of the frames to be outputted
    frames = []
    # # Loop over each frame in the animated image
    for i,frame in enumerate(ImageSequence.Iterator(im)):
        # Draw the text on the frame
        d = ImageDraw.Draw(frame)
        txtoff = 0.03 * im.size[1]  # text offset from the borders in px

        d.text((im.size[0]//2, txtoff), target, font=font2, anchor='mm', fill="white")
        d.text((txtoff, im.size[1]-txtoff), telescope, font=font, anchor='lm', fill="white")
        d.text((im.size[0]-txtoff, im.size[1]-txtoff), date[i], font=font, anchor='rm', fill="white")
        d.text((im.size[0]-txtoff, im.size[1]-2*txtoff), f"{i+1} / {n}", font=font, anchor='rm', fill="white")

        
        if len(pos) > 0:
            # draw arrows
            pts = np.array(pos[i])
            off = np.array([0.02*im.size[1], 0.02*im.size[1]])
            pts += 0.015*im.size[1] # shift arrow wrt the source
            #print(off)
            arrowedLine(d,
                        tuple(pts + off),
                        tuple(pts),
                        width=2, color=(255,255,255))
        del d

        b = io.BytesIO()
        frame.save(b, format="GIF")
        frame = Image.open(b)
        #frame = ImageOps.flip(frame)
        frames.append(frame)
    # Quantize to reduced palette
    frames = [f.quantize(colors=16, method=Image.Quantize.MAXCOVERAGE) 
                  for f in frames]
    # Save the frames as a new image
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], optimize=True)


def add_circles(gif_path, pos, aprad=7):
    from PIL import Image, ImageDraw, ImageSequence, ImageFont
    import io

    im = Image.open(gif_path)

    # A list of the frames to be outputted
    frames = []
    r = aprad
    # # Loop over each frame in the animated image
    for i,frame in enumerate(ImageSequence.Iterator(im)):
        d = ImageDraw.Draw(frame)
        x, y = pos[i][0], pos[i][1]
        d.ellipse(
            [x - r, y - r, x + r, y + r],
            outline="dodgerblue",
            width=1
            )
        del d

        b = io.BytesIO()
        frame.save(b, format="GIF")
        frame = Image.open(b)
        frames.append(frame)
    # Quantize to reduced palette
    frames = [f.quantize(colors=16, method=Image.Quantize.MAXCOVERAGE) 
                  for f in frames]
    # Save the frames as a new image
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], optimize=True)


def get_images(fnames, size=None, position=None, coordinates=None, bkgsub=False,
               get_ast_pos=True, file_ap_pos=None):
    """
    """

    data_list = []
    fits_infos_list = []
    pos_ast_list = []

    if coordinates:
        if len(coordinates[0]) == 3 and len(coordinates[1]) == 3:
            ra, dec = coordinates
            ra = 15*(ra[0] + ra[1]/60 + ra[2]/3600)
            dec = dec[0] + dec[1]/60 + dec[2]/3600

    if file_ap_pos:
        ap_coord = np.genfromtxt(file_ap_pos, dtype=[('filename', 'S50'),
                                                    ('ra', float),
                                                    ('dec', float),
                                                    ('MJD', float)],
                                                    names=True)

    get_pos = False
    ap_pos_list = []
    for fname in tqdm(fnames):
        data, header, fits_infos = get_fits_infos(fname)
        wcs = WCS(header)
        if coordinates and get_pos:
            x, y = wcs.world_to_pixel(SkyCoord(ra=ra, dec=dec, unit="deg"))
            pos = [float(x), float(y)]
            pos_ast = get_astpx(data, fits_infos, wcs, centroid=False, display=False)
            if size:
                pos_ast = np.array(pos_ast) - np.array(pos) + np.array(size)//2
            pos_ast[1] = size[1]//2 - pos_ast[1] + size[1]//2 # Flip y  TODO: take care of meridian flip
        elif not position and get_pos:
            pos = get_astpx(data, fits_infos, wcs, centroid=False, display=False)
            pos_ast = pos
        else:
            pos = position
        
        if get_pos:
            pos_ast_list.append(pos_ast)

        if get_ast_pos and (not position):
            import fits_asteroid as fa
            data, header, fits_infos = fa.get_fits_infos(fname)
            wcs = WCS(header)
            ra, dec, x, y = fa.get_astpx(data,
                                  fits_infos,
                                  wcs, 
                                  centroid=False,
                                  display=False)
            pos = x,y

        # Background subtraction
        if bkgsub:
            data = bkgsub_array(data, display=False)[0]
        # Cropping
        if size or pos:
            if not size:
                size = data.shape
            data = cropping(data, size=size, position=pos, wcs=wcs, display=False)

        if file_ap_pos:
            x_ap, y_ap = wcs.world_to_pixel(SkyCoord(ra=ap_coord['RA'][i], dec=ap_coord['Dec'][i], unit="deg"))
            y_ap = data.shape[0] - y_ap
            ap_pos_list.append([x_ap, y_ap])  
              
        data_list.append(data)
        fits_infos_list.append(fits_infos)

    return data_list, fits_infos_list, pos_ast_list, ap_pos_list


def make_gif(fnames, destination, filename, gif_factor=0.25, z=0.05, delay=0.2,
                 size=None, position=None, coordinates=None, bkgsub=False,
                 write_text=False, scaling_type='zscale', get_ast_pos=True,
                 file_ap_pos=None, aprad=7):
    """
    """
    folder_exist(destination)

    if filename == 'dir':
        filename = f"{str(Path(fnames[0]).absolute().parent).split('/')[-1]}"
    if ".gif" not in filename:
        filename = "{}.gif".format(filename)
    
    gif_path = os.path.join(destination, filename)

    get_images_res = get_images(fnames,
                                size=size, position=position, coordinates=coordinates,
                                bkgsub=bkgsub, get_ast_pos=get_ast_pos)
    data_list, fits_infos_list, pos_list, ap_pos_list = get_images_res

    data_list_resized = [resize(data, (np.array(np.shape(data)) * gif_factor).astype(int), anti_aliasing=True)
                                for data in data_list]

    #print(scaling_type)
    if scaling_type == 'zscale_uni':
        z_scale_limits_inf = []
        z_scale_limits_sup = []
        for data in data_list_resized:
            limits = z_scale(data, c=z, verbose=False, return_limits=True)[1]
            z_scale_limits_inf.append(limits[0])
            z_scale_limits_sup.append(limits[1])
        z_scale_limit_inf = np.median(z_scale_limits_inf)
        z_scale_limit_sup = np.median(z_scale_limits_sup)
        data_list_scaled = [manual_scale(data, vmin=z_scale_limit_inf, vmax=z_scale_limit_sup)
                            for data in data_list_resized]
    elif scaling_type == 'zscale':
        data_list_scaled = [z_scale(data, c=z)
                            for data in data_list_resized]
    elif scaling_type == 'uni_perct':
        data_list_scaled = [manual_scale(np.nan_to_num(data, nan=0.0),
                                         vmin=np.percentile(data[data != 0], 5),
                                         vmax=np.percentile(data[data != 0], 99))
                            for data in data_list_resized]
    else:
        data_list_scaled = [data for data in data_list_resized]

    data_list = [np.flip(data, axis=0) for data in data_list_scaled]
    data_list = [(data * 255).astype("uint8") for data in data_list]
    frames = [Image.fromarray(data) for data in data_list]
    # Quantize to reduced palette
    frames = [f.quantize(colors=16, method=Image.Quantize.MAXCOVERAGE) 
                  for f in frames]
    # Save the frames as a new image
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        #fps=1/(delay*1000),
        duration=delay*1000, # duration is in ms
        loop=0,
        optimize=True    # additional size optimization
    )
    
    if write_text:
        pos_list = np.array(pos_list) * gif_factor
        gif_text(gif_path, fits_infos_list, pos=pos_list)
    
    if file_ap_pos:
        add_circles(gif_path, ap_pos_list, aprad=aprad)
    
    print(f"> Gif saved to {gif_path}")

if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description='Make gif from FITS images')

    parser.add_argument("fnames", help='input FITS files', nargs='+')
    parser.add_argument("-d", "--destination", help='destination folder',
                        default=".", type=str)
    parser.add_argument("-n", "--gifname", help='output gif name',
                        default="mygif", type=str)
    parser.add_argument("-f", "--gif_factor", help='gif factor for resizing (default=0.25)',
                        default=0.25, type=float)
    parser.add_argument("-i", "--images",
                        help='enable creation of the individual PNG images\
                              instead of the gif', action='store_true')
    parser.add_argument("-st", "--stack",
                        help='enable creation of stacked image\
                              instead of the gif', action='store_true')
    parser.add_argument("-z", "--z_scale", help='z scaling factor (default=0.05)',
                        default=0.05, type=float)
    parser.add_argument("-dl", "--delay", help='delay between images (default=0.2s)',
                        default=0.2, type=float)
    parser.add_argument("-s", "--skip", help='skip a certain number of images',
                        default=1, type=int)
    parser.add_argument('-sz','--size', help='Crop size(s)', nargs='+')
    parser.add_argument("-p", "--position",
                        help="Crop position coordinates", nargs='+') 
    parser.add_argument('-nw','--no_warnings',
                        help='Suppress Astropy warnings',
                        action='store_true')
    parser.add_argument('-b','--bkgsub',
                        help='Enable bkg subtraction',
                        action='store_true')
    parser.add_argument('-wt','--write_text',
                        help='Enable text infos on gif',
                        action='store_true')
    parser.add_argument('-sctype','--scaling_type',
                        help='Type of image scaling to use',
                        choices=['zscale', 'zscale_uni', 'uni_perct'],
                        default='zscale')
    parser.add_argument("-app", "--file_ap_pos", help='output gif name',
                        default="", type=str)
    parser.add_argument("-aprad", "--aprad", help='Photometric aperture radius',
                        default=7, type=float)


    args = parser.parse_args()

    fnames = sorted(args.fnames)
    destination = args.destination
    gifname = args.gifname
    gif_factor = args.gif_factor
    z = args.z_scale
    dl = args.delay
    s = args.skip
    size = args.size
    position = args.position
    bkgsub = args.bkgsub
    no_warnings = args.no_warnings
    scaling_type = args.scaling_type

    images = args.images
    stack = args.stack
    write_text = args.write_text

    file_ap_pos = args.file_ap_pos
    aprad = args.aprad

    if no_warnings:
        import warnings
        from astropy.utils.exceptions import AstropyWarning
        warnings.simplefilter('ignore', category=AstropyWarning)

    if size:
        size = [int(sz) for sz in args.size]
        if len(size) == 1: # If only one size is specified, use square
            size = [size[0],size[0]]
    if position:
        position = [int(p) for p in position]

    make_gif(fnames[::s], destination, gifname, gif_factor=gif_factor,
                     z=z, delay=dl,
                     bkgsub=bkgsub,
                     size=size, position=position,
                     write_text=write_text,
                     get_ast_pos=True, # TODO put in args cmd line
                     scaling_type=scaling_type,
                     #coordinates=[(21,32,22), (-0,-14,-29)]
                     file_ap_pos=file_ap_pos,
                     aprad=aprad
                     )
