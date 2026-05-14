# phot_clean_stars

Clean star contamination in asteroid photometry

----

These scripts aim at correcting star contamination when an asteroid moves
close to background stars. Photometry must be done with [Photometry Pipeline (PP)](https://github.com/marinferrais/photometrypipeline).
A normal PP run is used to obtain the ZP for each images. Then the star are removed by taking the median of images before and after each images and subtracting it. The asteroid instrumental magnitudes are obtained from these star cleaned images, using the apertures position used for the original images.


## Installation

### Prerequisites
- [Photometry Pipeline (PP)](https://github.com/marinferrais/photometrypipeline) must be installed in a conda environment.

- ffmpeg:  
Depending on your distribution: 
```bash
sudo apt update && sudo apt install ffmpeg
sudo snap install ffmpeg
sudo dnf install ffmpeg
sudo pacman -S ffmpeg
```  

### Steps

1. Clone the repository:
```bash
git clone https://github.com/marinferrais/phot_clean_stars
```

2. Install dependencies in the same conda env than PP (here pp):
```bash
conda activate pp
conda install -c conda-forge photutils reproject
```

3. Add to your .bashrc with the path to where you installed:
```text
# phot_clean_stars
export PATH=$PATH:$HOME/phot_clean_stars
export PYTHONPATH="${PYTHONPATH}:$HOME'/phot_clean_stars"
```

## Usage

In the directory where your FITS files are:
```bash
phot_clean_star.sh -rp
```

Change FITS_FILES pattern in phot_clean_star.sh if necessary ("*fits" by default)

Check phot_clean_star.sh to see the different cmd line arguments available and their default values.

Some are related to PP:
```text
-target    # target name
-solar     # use only star with solar-like color
-filter    # calibrate to this band
-aprad     # radii in px to use a fixed aperture
-aprad_tar # aperture size for the target only, use same as aprad if not given
```

Some are related to the diagnostic gifs:
```text
-sz # cutout size in pixel
-gsz # gif size in pixel
-df # delay between frame (s)
```

Some are related to the star cleaning:
```text
-k # number of images to use in the median
-p # number of images before of after not used in the median, very important for slow targets
```

To not redo an existing PP run use:
```text
-s_pp
```



