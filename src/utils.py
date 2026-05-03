"""General utility functions for file/folder and math operations"""

import os
import shutil
from math import pi, sin, cos
from datetime import datetime

from src.paths import INPUT_DIR, HYDROINF_RESULTS_DIR

import pandas as pd


def create_output_folder():
    """
    Create a new folder with a timestamp as its name inside the 'Results' folder.

    Returns:
        str: The path to the created folder.
    """
    HYDROINF_RESULTS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_folder = HYDROINF_RESULTS_DIR / f"output_{timestamp}"
    os.makedirs(output_folder, exist_ok=True)

    return output_folder


def copy_input_folder(output_folder, case_name):
    """
    Copy the entire input folder to the new output folder.

    Args:
        output_folder (str): The path to the output folder.
        case_name (str): Name of the case/simulation.

    Returns:
        str: The path to the INP file in the new folder.
    """
    shutil.copytree(INPUT_DIR, output_folder, dirs_exist_ok=True)
    return os.path.join(output_folder, f'{case_name}.inp')


def delete_files(output_folder, file_extensions):
    """
    Delete all files in the output folder with the given extensions.

    Args:
        output_folder (str): The path to the output folder.
        file_extensions (list): List of file extensions to delete.
    """
    count = 0
    #print(f"Deleting files with extensions {file_extensions} from {output_folder}")
    for file in os.listdir(output_folder):
        if any(file.endswith(ext) for ext in file_extensions):
            os.remove(os.path.join(output_folder, file))
            count += 1
    #print(f"Deleted {count} files from {output_folder}")

def get_angle_between_points(num_vars):
    """
    Calculate the angles between the points by the number of points.
    Args:
        num_vars: number of variables
    Returns:
        list(float): List of angles in radians.
    """
    angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
    angles += angles[:1]
    return angles


def calculate_polygon_area(values):
    """
    Calculate the area of the polygon using the Shoelace formula.

    Args:
        values: Normalized values.

    Returns:
        float: The area of the polygon.
    """
    num_vars = len(values)
    angles = get_angle_between_points(num_vars)
    values += values[:1]
    #values = np.array([float(value) for value in values])

    x = [value * cos(angle) for value, angle in zip(values, angles)]
    y = [value * sin(angle) for value, angle in zip(values, angles)]
    area = 0.5 * abs(sum(x[i] * y[i + 1] - y[i] * x[i + 1] for i in range(num_vars)))
    return area


def combine_conduit_result_files(raw_results_folder):
    """
    Combine all conduit result files into a single DataFrame.
    This function reads the registry of processed conduits and aggregates the results from all conduit files.
    Args:
        raw_results_folder (str): Path to the folder containing raw results.
    Returns:
        pd.DataFrame: Combined results from all conduit files.
    """
    registry_path = os.path.join(raw_results_folder, 'processed_conduits.csv')
    # Check if the registry exists
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"No processed conduits registry found at {registry_path}")

    # Read the registry of processed conduits
    registry = pd.read_csv(registry_path)
    print(f"Found {len(registry)} processed conduits")

    # Aggregate results from all conduit files
    conduit_files = [os.path.join(raw_results_folder, f'conduit_{conduit}_results.csv')
                     for conduit in registry['conduit']
                     if os.path.exists(os.path.join(raw_results_folder, f'conduit_{conduit}_results.csv'))]

    if not conduit_files:
        raise ValueError("No conduit result files found")

    # Use pd.concat only once on the list of DataFrames
    combined_results = pd.concat([pd.read_csv(file) for file in conduit_files], ignore_index=True)

    return combined_results


def create_conduit_names_from_range(start, end):
    """
    Create a list of conduit names from a given range.

    Args:
        start (int): Starting number for the conduit names.
        end (int): Ending number for the conduit names.

    Returns:
        list: List of conduit names in the format 'C{number}'.
    """
    return [f'C{i}' for i in range(start, end + 1)]


def get_missing_pipes(all_conduits, raw_results_folder):
    """
    Gets a list of all conduits and a path to the raw results' folder.
    Checks which conduits do not have a csv results raw results file and which don't appear in the processed_conduits.csv file.
    Args:
        all_conduits (list): Names of all conduits.
        raw_results_folder (str): Path to the folder containing raw results.
    Returns:
        list: List of conduits that need to be run.
    """
    # get a list of conduits that have a results csv file in the format conduit_{conduit}_results.csv
    raw_results_conduits = []
    for file in os.listdir(raw_results_folder):
        if file.startswith('conduit_') and file.endswith('_results.csv'):
            conduit_name = file[len('conduit_'):-len('_results.csv')]
            raw_results_conduits.append(conduit_name)

    # get a list of conduits that are in the processed_conduits.csv file
    registry_path = os.path.join(raw_results_folder, 'processed_conduits.csv')
    processed_conduits = []
    if os.path.exists(registry_path):
        registry = pd.read_csv(registry_path)
        processed_conduits = registry['conduit'].tolist()

    # get all conduits that appear in raw_results_conduits but not in processed_conduits
    add_to_processed_conduits = list(set(processed_conduits) - set(raw_results_conduits))
    print("Add to processed_conduits.csv: Conduits in raw results but not in processed_conduits.csv")
    print(add_to_processed_conduits)
    # get all conduits that are in processed_conduits but not in raw_results_conduits
    find_raw_results = list(set(raw_results_conduits) - set(processed_conduits))
    print("Find raw results files: Conduits in processed_conduits.csv but not in raw results:")
    print(find_raw_results)
    # get all conduits that are in all_conduits but not in processed_conduits and not in raw_results_conduits
    conduits_to_run = list(set(all_conduits) - set(raw_results_conduits) - set(processed_conduits))
    print("Conduits to run: Conduits in all_conduits but not in processed_conduits.csv and not in raw results:")
    print(conduits_to_run)
    return conduits_to_run


