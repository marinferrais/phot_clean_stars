
def tel2code(telescope_name, key_exists=False, invert=False):

    name_dict = {'TN':'Z53',
                 'TS':'I40',
                 'SSO2':'W75',  # Europa, SPECULOOS-South Observatory, Paranal
                 'SNO1':'Z25',  # Artemis - Teide Observatory
                 'Artemis':'Z25',  # Artemis - Teide Observatory
                 'DTC':'690',   # Lowell Observatory, Flagstaff
                 'LDT':'690',   # Lowell Observatory, Flagstaff
                 'LO':'699',    # Lowell Observatory - LONEOS
                 'MO':'J43',    # MOSS - Oukaimeden Observatory
                 'MOSS':'J43',  # MOSS - Oukaimeden Observatory
                 'C2PU':'010',  # Caussols
                 'LT':'J13',    # La Palma-Liverpool Telescope
                 'BMO':'Q68',   # Julian Oey - Blue Mountains Observatory, Leura
                 'BW':'U82',    # Brian Warner - use above
                 'CS3':'U82',   # Warner - CS3-Palmer Divide Station, Landers
                 'CS3':'U81',   # Stephens - CS3-Trojan Station, Landers 
                 'SMP':'104',   # San Marcello Pistoiese
                 'D65':'557',   # Petr Pravec - Ondrejov
                 'DK154':'W74', # Danish Telescope, La Silla
                 'JWST/MIRI':'@jwst',# JWST
                 'GO':'517',    # Geneva Observatory
                 'NOA':'066',   # National Observatory of Athens
                 'CAHA':'493',  # Lowell Observatory, Anderson Mesa Station
                 'SW09m':'691', # Spacewatch 0.9-m
                 'OGS':'J04',   # ESA Optical Ground Station - Teide
                 'IAC80':'954', # Teide observatory (here for IAC80 which does not have its own code?)
                 'SAO':'K90',   # Sopot Astronomical Observatory
                 'BO':'L54',    # Berthelot Observatory
                 'OASI':'Y28',  # OASI, Nova Itacuruba
                 'OdP':'K11',   # Observatoire de Pommier
                 'Helms':'V24', # Sonoran Desert Skies Obs, observer: Alex Helms
                 'Lulin':'D35', # Lulin Obs
                 'RO':'W39', # Robinson Obs
                 'TTT3':'Y68',
                 'TTT1':'Y65',
                 } 

    if key_exists:
        return telescope_name in name_dict.keys()

    else:
        if invert:
            name_dict = {v: k for k, v in name_dict.items()}
        
        try:
            return name_dict[str(telescope_name)]
        except ValueError:
            print(f'> Code for {telescope_name} not defined in {name_dict}')
