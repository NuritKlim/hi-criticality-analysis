"""Handles the analysis and processing of simulation data"""
import os
import gc
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from datetime import datetime
from tqdm import tqdm

from pyswmm import SimulationPreConfig

from src.simulation import (get_accumulated_flows)
from src.utils import (calculate_polygon_area)


def get_accumulated_flows_by_ratios(input_file, conduit, height, ratios, tolerance, baseline_flows=None):
    """
    Change the height of the specified conduit for each given ratio,
    run simulations and analyze flow values. Returns raw (non-normalized) results.
    """
    if baseline_flows is None:
        baseline_flows = get_accumulated_flows(input_file)
    baseline_sum = sum(baseline_flows.values())
    baseline_specific_sum = baseline_flows.get(conduit, 0)

    # Create DataFrame for raw, non-normalized data
    raw_results = pd.DataFrame(columns=['conduit', 'ratio', 'accum_flow_sum', 'specific_conduit_flow_sum',
                                        'affected_conduits', 'total_conduits'])

    # Process baseline case (ratio=1.0) first
    baseline_row = pd.DataFrame({
        'conduit': [conduit],
        'ratio': [1.0],
        'accum_flow_sum': [baseline_sum],
        'specific_conduit_flow_sum': [baseline_specific_sum],
        'affected_conduits': [0],
        'total_conduits': [len(baseline_flows)]
    })

    # Create array of non-baseline ratios to process
    non_baseline_ratios = [r for r in ratios if r != 1.0]

    if non_baseline_ratios:
        # Process all other ratios in batch where possible
        non_baseline_results = []

        for ratio in tqdm(non_baseline_ratios, desc=f"Processing ratios for conduit {conduit}"):
            new_height = float(height) * ratio
            sim_conf = SimulationPreConfig()
            sim_conf.add_update_by_token("XSECTIONS", conduit, 2, new_val=new_height)

            conduit_flows = get_accumulated_flows(input_file, sim_preconfig=sim_conf)
            accum_flow_sum = sum(conduit_flows.values())
            specific_conduit_flow_sum = conduit_flows.get(conduit, 0)

            # Vectorized check for affected conduits
            common_keys = set(baseline_flows.keys()) & set(conduit_flows.keys())
            baseline_values = np.array([baseline_flows[k] for k in common_keys if k != conduit])
            current_values = np.array([conduit_flows[k] for k in common_keys if k != conduit])

            # Create masks for zero and non-zero flow values
            significant_flow = (np.abs(baseline_values) >= 1e-6) | (np.abs(current_values) >= 1e-6)

            # Add a small epsilon to avoid division by zero
            epsilon = 1e-10
            relative_error = np.abs((current_values - baseline_values) / (baseline_values + epsilon))

            within_tolerance = relative_error <= tolerance

            # Count affected conduits
            affected_conduits = np.sum(significant_flow & ~within_tolerance)

            non_baseline_results.append({
                'conduit': conduit,
                'ratio': ratio,
                'accum_flow_sum': accum_flow_sum,
                'specific_conduit_flow_sum': specific_conduit_flow_sum,
                'affected_conduits': affected_conduits,
                'total_conduits': len(conduit_flows)
            })

            # Clear conduit_flows from memory as it's no longer needed after this iteration
            del conduit_flows
            # Clear arrays that are no longer needed
            del baseline_values, current_values, significant_flow, within_tolerance

        # Combine baseline with other results
        if non_baseline_results:
            non_baseline_df = pd.DataFrame(non_baseline_results)
            raw_results = pd.concat([baseline_row, non_baseline_df], ignore_index=True)

            # Clean up large temporary objects
            del non_baseline_results, non_baseline_df
        else:
            raw_results = baseline_row
    else:
        raw_results = baseline_row

    return raw_results


def calculate_radar_polygon_area(row):
    """
    Calculate the area of the polygon created by the normalized
    points representing the measures in the radar chart.

    Args:
        row: A row from the DataFrame containing normalized values.

    Returns:
        float: The area of the polygon.
    """

    values = [row['norm_accum_flow_sum'], row['norm_specific_conduit_flow_sum'], row['unaffected_conduits_ratio']]

    return calculate_polygon_area(values)


def save_conduit_results(results_df, output_folder, conduit):
    """
    Save the raw results for a single conduit to a CSV file.

    Args:
        results_df (DataFrame): DataFrame with raw simulation results
        output_folder (str): Folder to save the results
        conduit (str): Conduit ID
    """
    # Create a subfolder for raw results if it doesn't exist
    raw_results_folder = os.path.join(output_folder, 'raw_results')
    os.makedirs(raw_results_folder, exist_ok=True)

    # Save to CSV - one file per conduit
    csv_path = os.path.join(raw_results_folder, f'conduit_{conduit}_results.csv')
    results_df.to_csv(csv_path, index=False)

    # Update the registry of processed conduits
    registry_path = os.path.join(raw_results_folder, 'processed_conduits.csv')

    if os.path.exists(registry_path):
        registry = pd.read_csv(registry_path)
        if conduit not in registry['conduit'].values:
            new_entry = pd.DataFrame(
                {'conduit': [conduit], 'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]})
            registry = pd.concat([registry, new_entry], ignore_index=True)
    else:
        registry = pd.DataFrame({'conduit': [conduit], 'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]})

    registry.to_csv(registry_path, index=False)

    return csv_path


def calculate_pca_score(normalized_results):
    """
    Calculate PCA-based scores for conduits using the normalized measures.

    Args:
        normalized_results (DataFrame): DataFrame containing normalized measures

    Returns:
        numpy.ndarray: PCA scores (first principal component) for each conduit
    """
    # Extract the normalized measures
    features = normalized_results[['norm_accum_flow_sum',
                                   'norm_specific_conduit_flow_sum',
                                   'unaffected_conduits_ratio']].values

    # Apply PCA directly (no scaling needed since features are already normalized)
    pca = PCA(n_components=1)
    pca_scores = pca.fit_transform(features)

    # Get analysis information
    explained_variance_ratio = pca.explained_variance_ratio_[0]
    print(f"PCA explained variance ratio for first component: {explained_variance_ratio:.5f}")
    components = pca.components_[0]  # Loadings for each feature
    print(f"PCA components (loadings): {components}")

    return pca_scores.flatten()

def run_conduit_simulations(conduits, input_file, output_folder, ratios, tolerance):
    """
    Run simulations for specified conduits and save raw results.
    This is the main function for Part 1 of the distributed workflow.

    Args:
        conduits (dict): Dictionary of conduits and their heights.
        input_file (str): Path to the INP file.
        output_folder (str): Path to the output folder.
        ratios (list): List of ratios by which to change the height.
        tolerance (float): Tolerance for flow value comparison.

    Returns:
        list: Paths to the saved result files
    """
    baseline_flows = get_accumulated_flows(input_file)
    print(f"Baseline flows calculated for {len(baseline_flows)} conduits")

    result_files = []

    for conduit in tqdm(conduits, desc="Processing conduits"):
        # Get raw results for this conduit
        raw_results = get_accumulated_flows_by_ratios(
            input_file, conduit, conduits[conduit], ratios, tolerance, baseline_flows
        )
        gc.collect()

        # Normalize the accumulated flow values
        raw_results['norm_accum_flow_sum'] = (raw_results['accum_flow_sum'] - raw_results['accum_flow_sum'].min()) / (
                raw_results['accum_flow_sum'].max() - raw_results['accum_flow_sum'].min())
        raw_results['norm_specific_conduit_flow_sum'] =(raw_results['specific_conduit_flow_sum'] - raw_results[
            'specific_conduit_flow_sum'].min()) / (raw_results['specific_conduit_flow_sum'].max() - raw_results[
            'specific_conduit_flow_sum'].min())
        raw_results['unaffected_conduits_ratio'] = 1 - ((raw_results['affected_conduits']) / (raw_results['total_conduits']))

        # Save results to file
        result_file = save_conduit_results(raw_results, output_folder, conduit)
        result_files.append(result_file)

        # Create individual conduit plots (optional)
        #plot_accumulated_flows(raw_results, conduit, output_folder)

        # Clean up the raw_results DataFrame after saving
        del raw_results

    return result_files


def get_stats(conduits_data, output_folder):
    """
    Calculate statistics for conduits_data and save to a file.
    Optimized using NumPy for improved performance with large datasets.

    Args:
        conduits_data (DataFrame): DataFrame with conduit names and flow values.
        output_folder (str): The folder to save the statistics file.

    Returns:
        set: A set of top conduits for visualization.
    """
    # Convert to numpy arrays just once at the beginning
    conduit_names = conduits_data['conduit'].to_numpy()

    # Define measures to analyze
    measure_names = [
        'accum_flow_sum',
        'specific_conduit_flow_sum',
        'affected_conduits',
        'unaffected_conduits_ratio',
        'measures_sum',
        'polygon_area',
        'pca_score',
    ]

    # Create a structured dictionary to store all results
    stats = {}
    # Create a set to keep top conduits for visualization
    top_conduits = set()

    # Process each measure
    for measure_name in measure_names:
        # Extract values as NumPy array for faster processing
        values = conduits_data[measure_name].to_numpy(dtype=np.float64)

        # Find top 3 max values using NumPy's argpartition (faster than argsort for partial sorting)
        # argpartition is O(n) while argsort is O(n log n)
        top_3_max_indices = np.argpartition(values, -3)[-3:]
        # Sort these 3 indices by their values in descending order
        top_3_max_indices = top_3_max_indices[np.argsort(-values[top_3_max_indices])]
        top_3_max = [(conduit_names[i], float(values[i])) for i in top_3_max_indices]

        # Find top 3 min values
        top_3_min_indices = np.argpartition(values, 3)[:3]
        # Sort these 3 indices by their values in ascending order
        top_3_min_indices = top_3_min_indices[np.argsort(values[top_3_min_indices])]
        top_3_min = [(conduit_names[i], float(values[i])) for i in top_3_min_indices]

        # Standard deviation
        std_dev = float(np.std(values))

        stats[measure_name] = {
            'top_3_max': top_3_max,
            'top_3_min': top_3_min,
            'std_dev': std_dev
        }
        # Store top conduits for visualization without duplicates
        top_conduits.update([conduit_names[i] for i in top_3_max_indices])
        top_conduits.update([conduit_names[i] for i in top_3_min_indices])

    # Write all values and statistics to a file
    stats_file_path = os.path.join(output_folder, 'statistics.txt')
    with open(stats_file_path, 'w') as f:
        # Write header for all conduit values
        f.write("All measures for each conduit:\n")
        f.write(
            'conduit,ratio,accum_flow_sum,specific_conduit_flow_sum,affected_conduits,'
            'norm_accum_flow_sum,norm_specific_conduit_flow_sum,unaffected_conduits_ratio,'
            'measures_sum,norm_measures_sum,polygon_area,norm_polygon_area\n'
        )

        # Use NumPy's fast iteration with nditer if needed for large datasets
        for _, row in conduits_data.iterrows():
            f.write(
                f"{row['conduit']}, {row['accum_flow_sum']}, {row['specific_conduit_flow_sum']}, "
                f"{row['affected_conduits']}, {row['norm_accum_flow_sum']}, {row['norm_specific_conduit_flow_sum']}, "
                f"{row['unaffected_conduits_ratio']}, {row['measures_sum']}, {row['norm_measures_sum']}, "
                f"{row['polygon_area']}, {row['norm_polygon_area']}\n"
            )

        # Write statistics
        f.write("\nStatistics:\n")
        for measure_name, measure_stats in stats.items():
            f.write(f"\n{measure_name}:\n")
            f.write(f"Top 3 Max: {measure_stats['top_3_max']}\n")
            f.write(f"Top 3 Min: {measure_stats['top_3_min']}\n")
            f.write(f"Standard Deviation: {measure_stats['std_dev']:.4f}\n")

    print(f"Measures and statistics saved to {stats_file_path}")
    return top_conduits


def normalize_combined_results(combined_results):
    """
    Normalize the combined results from all conduits using NumPy for improved performance.

    Args:
        combined_results (DataFrame): Combined raw results from all conduits.

    Returns:
        DataFrame: Normalized results
    """
    # Group by conduit to get summaries - keep this as DataFrame for now
    conduit_summaries = combined_results.groupby('conduit').agg({
        'accum_flow_sum': 'sum',
        'specific_conduit_flow_sum': 'sum',
        'affected_conduits': 'max',
        'total_conduits': 'first'  # Just need one value per conduit
    }).reset_index()

    # Extract conduit IDs to preserve order
    conduit_ids = conduit_summaries['conduit'].values

    # Extract NumPy arrays for faster numerical operations
    accum_flow = conduit_summaries['accum_flow_sum'].values
    specific_flow = conduit_summaries['specific_conduit_flow_sum'].values
    affected = conduit_summaries['affected_conduits'].values
    total = conduit_summaries['total_conduits'].values

    # Perform normalizations using NumPy operations (faster than DataFrame operations)
    # Normalize accumulated flow sum
    accum_flow_min = np.min(accum_flow)
    accum_flow_range = np.max(accum_flow) - accum_flow_min
    norm_accum_flow = (accum_flow - accum_flow_min) / accum_flow_range if accum_flow_range != 0 else np.zeros_like(
        accum_flow)

    # Normalize specific conduit flow sum
    specific_flow_min = np.min(specific_flow)
    specific_flow_range = np.max(specific_flow) - specific_flow_min
    norm_specific_flow = (
                                     specific_flow - specific_flow_min) / specific_flow_range if specific_flow_range != 0 else np.zeros_like(
        specific_flow)

    # Calculate unaffected conduits ratio
    unaffected_ratio = 1 - (affected / total)

    # Create result DataFrame with both original and normalized values
    result_df = pd.DataFrame({
        'conduit': conduit_ids,
        'accum_flow_sum': accum_flow,
        'specific_conduit_flow_sum': specific_flow,
        'affected_conduits': affected,
        'total_conduits': total,
        'norm_accum_flow_sum': norm_accum_flow,
        'norm_specific_conduit_flow_sum': norm_specific_flow,
        'unaffected_conduits_ratio': unaffected_ratio
    })

    return result_df


def get_scores_from_normalized_results(output_folder, normalized_results):
    """
    Create scores from normalized results for all conduits.
    1st score: A simple sum of normalized measures.
    2nd score: Polygon area based on normalized measures.
    3rd score: Reducing the dimensionality of the measures using PCA.

    Args:
        output_folder (str): Path to the folder containing raw results.
        normalized_results (DataFrame): DataFrame with raw simulation results for all conduits.

    Returns:
        DataFrame: Normalized results and scores for all conduits
    """

    # Calculate the sum of normalized measures
    normalized_results['measures_sum'] = normalized_results[
        ['norm_accum_flow_sum', 'norm_specific_conduit_flow_sum', 'unaffected_conduits_ratio']].sum(axis=1)
    normalized_results['norm_measures_sum'] = (normalized_results['measures_sum'] - normalized_results[
        'measures_sum'].min()) / (normalized_results['measures_sum'].max() - normalized_results['measures_sum'].min())


    # Calculate polygon areas
    normalized_results['polygon_area'] = normalized_results.apply(calculate_radar_polygon_area, axis=1)
    normalized_results['norm_polygon_area'] = (normalized_results['polygon_area'] - normalized_results[
        'polygon_area'].min()) / (normalized_results['polygon_area'].max() - normalized_results[
                                                  'polygon_area'].min())

    # Calculate PCA scores
    pca = calculate_pca_score(normalized_results)

    # Add PCA scores to the DataFrame
    normalized_results['pca_score'] = pca
    normalized_results['norm_pca_score'] = (normalized_results['pca_score'] - normalized_results['pca_score'].min()) / (
        normalized_results['pca_score'].max() - normalized_results['pca_score'].min())

    # Save the normalized results
    normalized_path = os.path.join(output_folder, 'normalized_results.csv')
    normalized_results.to_csv(normalized_path, index=False)

    return normalized_results
