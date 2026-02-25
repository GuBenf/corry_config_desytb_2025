import re
import os
import sys
import argparse
from glob import glob

def runCorry(config, files, log, additional=None):
    """
    Function to execute the Corry software with the given parameters.
    Args:
        config: The configuration file to use.
        files: A list of files required by the Corry program.
        log: Log file where the output will be saved.
        additional: Optional string with additional arguments to pass to the Corry program.
    # """

    dataDir = str(os.environ.get("TB_DATA"))
    telepixDir = dataDir+'/telepix2'

    cmd = f'corry -c {config} -o EventLoaderEUDAQ2.file_name={files[0]} -o EventLoaderEUDAQ2:TLU_0.file_name={files[1]} -o EventLoaderHDF5.filename={files[2]}   -o EventLoaderMuPixTelescope.input_file={files[3]} -o EventLoaderMuPixTelescope.input_directory={telepixDir} -l {log} '
    #cmd = f'./corry -c {config} -o EventLoaderEUDAQ2.file_name={files[0]} -o EventLoaderEUDAQ2:TLU_0.file_name={files[1]} -o EventLoaderHDF5.filename={files[2]} -l {log} '
    if additional:
        cmd += additional
    print('\n\n ####### RUNNING: ', cmd,'\n\n')  
    os.system(cmd)

def increase_iteration(filename):
    match = re.search(r"(it)(\d+)", filename)

    prefix, number = match.groups()
    number = int(number)
    new_filename = re.sub(r"(it)\d+", f"{prefix}{number + 1}", filename)

    return new_filename

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Run Corry software with specific configurations and data files.')
    
    # Define the arguments the script expects
    parser.add_argument('runNmb', type=int, help='Run number used to locate the data files.')
    parser.add_argument('initialGeo', type=str, help='Path to the initial geometry file.')
    parser.add_argument('finalGeo', type=str, help='Path to the final geometry file.')
    parser.add_argument('tel_id', type=int, help='Number of telescope id for the alignment')

    # Parse the arguments
    args = parser.parse_args()

    runNmb = args.runNmb
    initialGeo = args.initialGeo
    finalGeo = args.finalGeo
    tel_id = args.tel_id

    # Directory paths where the data is stored
    dataDir = str(os.environ.get("TB_DATA"))
    telDir = dataDir+'/telescope'
    tluDir = dataDir+'/tlu'
    dutDir = dataDir+'/dut'
    
    # List of directories where we need to search for files
    dirs = [telDir, tluDir]

    os.system(f'/usr/bin/python3 find_masked_pixel_analysis.py {runNmb}')

    geo_file_dir = os.path.dirname(finalGeo)
    prealignedGeo = os.path.join(geo_file_dir, "prealigned.geo")
    geo_file_template = os.path.join(geo_file_dir, f"geo_id{tel_id}_align_tel_it1")
    root_file_template = f"align_tel_id{tel_id}_it1.root"

    files = []

    # Globbing the telescope and TLU data files based on the run number
    # We use globbing to find files matching the specific run number pattern
    for d in dirs:
        print(f'Globbing for files in directory {d} with run number {runNmb:06}')
        files_found = glob(f'{d}/*run{runNmb:06}*.raw')
        if files_found:
            files.append(files_found[0])  # Append the first matched file
        else:
            print(f"No files found for run {runNmb:06} in {d}")
            sys.exit(1)  # Exit if no matching files are found

    # Globbing the DUT file based on the run number (converts to .h5 format)
    print(f'Globbing for DUT file with run number {runNmb:06}')
    dut_file_found = glob(dataDir+f'/dut/module_0/chip_0/run{runNmb:06}_converted.h5')
    if dut_file_found:
        files.append(dut_file_found[0])  # Append the first matched DUT file
    else:
        print(f"No DUT file found for run {runNmb:06}")
        sys.exit(1)

    # Globbing the telepix2 block file for the given run number
    print(f'Globbing for telepix2 block file for run {runNmb:06}')
    telepix_file_found = glob(dataDir+f'/telepix2/single_run_{runNmb:06}.blck')
    if telepix_file_found:
       files.append(os.path.basename(telepix_file_found[0]))  # Append the block file
    else:
       print(f"No telepix2 block file found for run {runNmb:06}")
       sys.exit(1)

    # Running the Corry software with different configuration files
    runCorry('prealign.conf', files, 'logs/log_prealign.txt', f'-o detectors_file={initialGeo} -o detectors_file_updated={prealignedGeo}')
    runCorry('align_mille.conf', files, 'logs/log_align_mille.txt', f'-o detectors_file={prealignedGeo} -o detectors_file_updated={geo_file_template} -o number_of_tracks=50000 -o histogram_file={root_file_template}')
    it2file = increase_iteration(geo_file_template)
    it2root = increase_iteration(root_file_template)
    runCorry('align_tel.conf', files, 'logs/log_align_tel.txt', f'-o detectors_file={geo_file_template} -o detectors_file_updated={it2file} -o number_of_tracks=50000 -o histogram_file={it2root}')
    it3root = increase_iteration(it2root)
    it3file = increase_iteration(it2file)
    runCorry('align_mille.conf', files, 'logs/log_align_mille.txt', f'-o detectors_file={it2file} -o detectors_file_updated={it3file} -o number_of_tracks=50000 -o histogram_file={it3root}')
    runCorry('align_dut.conf', files, 'logs/log_align_dut.txt', f'-o detectors_file={it3file} -o detectors_file_updated={finalGeo} -o number_of_tracks=50000 -o histogram_file={it3root}')

if __name__ == "__main__":
    main()
