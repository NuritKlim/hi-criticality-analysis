import os

from src.simulation import (
    get_conduits_from_input_file
)
from src.data_processing import (
    get_stats, get_scores_from_normalized_results, run_conduit_simulations, normalize_combined_results
)
from src.visualization import (
    visualize_risk,
)
from src.utils import (
    create_output_folder,
    copy_input_folder, delete_files,
    combine_conduit_result_files,
    get_missing_pipes
)
from src.paths import HYDROINF_RESULTS_DIR


def run_simulations_main(case_name='Astlingen_SWMM'):
    """
    Main function for Part 1: Running simulations for a subset of conduits.
    This can be run on different machines with different conduit subsets.
    """
    # Create output folder structure
    output_folder = create_output_folder()
    input_file = copy_input_folder(output_folder, case_name=case_name)

    # Define ratios for height modification (this is P)
    ratios = [1, 0.8, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02,
              0.01, 0.001]  # Can use more ratios when more detailed results are needed, or fewer ratios for faster runs.

    tolerance = 0.05  # Affected conduits tolerance (this is epsilon for C3)

    # Get all conduits from input file and their heights
    all_conduits = get_conduits_from_input_file(input_file)

    # Option 1: Process specific conduits by name
    # conduit_names = ['C1', 'C2', 'C3']  # Example of specific conduits
    # selected_conduits = {name: all_conduits[name] for name in conduit_names if name in all_conduits}

    # Option 2: Process conduits by index range (for distributed processing)
    # For example, machine 1 processes first half, machine 2 processes second half
    conduit_names = list(all_conduits.keys())
    start_idx = 0  # Change this for different machines
    end_idx = len(conduit_names)#//2  # Change this for different machines
    selected_subset = conduit_names[start_idx:end_idx]
    selected_conduits = {name: all_conduits[name] for name in selected_subset}

    # Option 3: Automatically find and process only missing conduits
    #selected_subset = get_missing_pipes(all_conduits, "output_folder\\raw_results")
    #selected_conduits = {name: all_conduits[name] for name in selected_subset}

    print(f"Processing {len(selected_conduits)} conduits out of {len(all_conduits)} total conduits")

    # Run simulations for the selected conduits
    run_conduit_simulations(
        selected_conduits, input_file, output_folder, ratios, tolerance
    )

    print(f"Simulation complete. Raw results saved to {output_folder}")

    # Delete unnecessary files from the output folder
    delete_files(output_folder, ['_mod.out', '_mod.rpt', '_mod.inp'])


def analyze_results_main(output_folder, case_name='Astlingen_SWMM'):
    """
    Main function for Part 2: Analyzing results from all simulation runs.
    This should be run after all simulations are complete.
    """
    # Specify the output folder containing all the raw results
    # This could be a merged folder with results from multiple machines
    raw_results_folder = os.path.join(output_folder, 'raw_results')
    conduit_results = combine_conduit_result_files(raw_results_folder)

    # Normalize results
    normalized_results = normalize_combined_results(conduit_results)
    scores = get_scores_from_normalized_results(output_folder, normalized_results)

    # Create the polygon area risk score dictionary for visualizations
    polygon_area_risk = scores[['conduit', 'norm_polygon_area']].set_index('conduit').to_dict()['norm_polygon_area']

    # Create visualizations of risk scores
    # This requires the original input file
    input_file = os.path.join(output_folder, f'{case_name}.inp')
    visualize_risk(polygon_area_risk, input_file, output_folder, 'Polygon_Area')

    pca_risk = scores[['conduit', 'norm_pca_score']].set_index('conduit').to_dict()['norm_pca_score']
    visualize_risk(pca_risk, input_file, output_folder, 'PCA')

    # Generate statistics
    top_conduits = get_stats(scores, output_folder)
    print(f"Top conduits: {top_conduits}")

    # Get conduits' list

    #conduits_to_plot = get_conduits_from_input_file(input_file)  # for plots for all conduits uncomment this line
    #conduits_to_plot = top_conduits  # for plots for top conduits uncomment this line
    #conduits_to_plot = ['C1', 'C2', 'C10'] # for plots for specific conduits uncomment this line
    #conduits_to_plot = create_conduit_names_from_range(10, 15) # for plots for a range of conduits uncomment this line

    #create_plots_for_conduits(conduits_to_plot, raw_results_folder, output_folder)

    print(f"Analysis complete. Results saved to {output_folder}")


if __name__ == "__main__":
    # To run simulations (Part 1):
    run_simulations_main(case_name='Astlingen_SWMM')  # Update case_name as needed

    # To analyze results (Part 2):
    # Uncomment this and comment out run_simulations_main() when ready to analyze
    # output_folder = HYDROINF_RESULTS_DIR / 'output_YYYYMMDD_HHMMSS'  # Update this path
    # analyze_results_main(output_folder, case_name='Astlingen_SWMM')