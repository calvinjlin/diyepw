import os
import pandas as pd
import argparse
import diyepw

# Set path to outputs produced by this script.
create_out_path  = os.path.abspath(os.path.join('..', 'outputs', 'create_amy_epw_files_output'))
if not os.path.exists(create_out_path):
    os.mkdir(create_out_path)

# Set path to where new EPW files should be saved.
amy_epw_file_out_path = os.path.join(create_out_path, 'epw')
if not os.path.exists(amy_epw_file_out_path):
    os.mkdir(amy_epw_file_out_path)

# Set path to the list of WMO stations for which new AMY EPW files should be created.
path_to_station_list = os.path.join('..', 'outputs', 'analyze_noaa_data_output', 'files_to_convert.csv')
if not os.path.exists(path_to_station_list):
    print(f"{path_to_station_list} does not exist. Please run analyze_noaa_isd_lite_files.py before running this script.")
    exit(1);

# Set path to the files where errors should be written
epw_file_violations_path = os.path.join(create_out_path, 'epw_validation_errors.csv')
errors_path = os.path.join(create_out_path, 'errors.csv')

# Ensure that the errors file is truncated
with open(errors_path, 'w'):
    pass

parser = argparse.ArgumentParser(
    description=f"""
        Generate epw files based on the files generated by unpack_noaa_data.py and analyze_noaa_data.py, which must
        be called prior to this script. The generated files will be written to {amy_epw_file_out_path}. A list of
        any files that could not be generated due to validation or other errors will be written to 
        {epw_file_violations_path} and {errors_path}.
    """
)
parser.add_argument('--max-records-to-interpolate',
                    default=6,
                    type=int,
                    help="""The maximum number of consecutive records to interpolate. See the documentation of the
                            pandas.DataFrame.interpolate() method's "limit" argument for more details. Basically,
                            if a sequence of fields up to the length defined by this argument are missing, those 
                            missing values will be interpolated linearly using the values of the fields immediately 
                            preceding and following the missing field(s). If a sequence of fields is longer than this
                            limit, then those fields' values will be imputed instead (see --max-records-to-impute)
                            """
)
parser.add_argument('--max-records-to-impute',
                    default=48,
                    type=int,
                    help=f"""The maximum number of records to impute. For groups of missing records larger than the
                            limit set by --max-records-to-interpolate but up to --max-records-to-impute, we replace the 
                            missing values using the average of the value two weeks prior and the value two weeks after 
                            the missing value. If there are more consecutive missing records than this limit, then the 
                            file will not be processed, and will be added to the error file at {errors_path}."""
)
args = parser.parse_args()

# Read in list of AMY files that should be used to create EPW files.
amy_file_list = pd.read_csv(path_to_station_list)
amy_file_list = amy_file_list[amy_file_list.columns[0]]

# Initialize the df to hold paths of AMY files that could not be converted to an EPW.
errors = pd.DataFrame(columns=['file', 'error'])

num_files = len(amy_file_list)
for idx, amy_file_path in enumerate(amy_file_list, start = 1):
    # The NOAA ISD Lite AMY files are stored in directories named the same as the year they describe, so we
    # use that directory name to get the year
    amy_file_dir = os.path.dirname(amy_file_path)
    year = int(amy_file_dir.split(os.path.sep)[-1])
    next_year = year + 1

    # To get the WMO, we have to parse it out of the filename: it's the portion prior to the first hyphen
    wmo_index = int(os.path.basename(amy_file_path).split('-')[0])

    # Our NOAA ISD Lite input files are organized under inputs/NOAA_ISD_Lite_Raw/ in directories named after their
    # years, and the files are named identically (<WMO>_<###>_<Year>.gz), so we can get the path to the subsequent
    # year's file by switching directories and swapping the year in the file name.
    s = os.path.sep
    amy_subsequent_year_file_path = amy_file_path.replace(s + str(year) + s, s + str(next_year) + s)\
                                                 .replace(f'-{year}.gz', f'-{next_year}.gz')
    try:
        amy_epw_file_path = diyepw.create_amy_epw_file(
            wmo_index=wmo_index,
            year=year,
            max_records_to_impute=args.max_records_to_impute,
            max_records_to_interpolate=args.max_records_to_interpolate,
            amy_epw_dir=amy_epw_file_out_path,
            amy_files=(amy_file_path, amy_subsequent_year_file_path)
        )

        print(f"Success! {os.path.basename(amy_file_path)} => {os.path.basename(amy_epw_file_path)} ({idx} / {num_files})")
    except Exception as e:
        errors = errors.append({"file": amy_file_path, "error": str(e)}, ignore_index=True)
        print(f"\n*** Error! {amy_file_path} could not be processed, see {errors_path} for details ({idx} / {num_files})\n")

print("\nDone!")

if not errors.empty:
     print(len(errors), f"files encountered errors - see {errors_path} for more information")
     errors.to_csv(errors_path, mode='w', index=False)

print(num_files - len(errors), f'files successfully processed. EPWs where written to {amy_epw_file_out_path}.')
