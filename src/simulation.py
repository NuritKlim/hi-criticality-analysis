"""Contains functions for working directly with SWMM simulations"""

import os
from pyswmm import Simulation, Links
from shapely import Point
from swmm_api import read_inp_file, read_rpt_file, read_out_file


def get_accumulated_flows(input_file, conduits = None, sim_preconfig=None, step_advance=300):
    """
    Run the simulation and accumulate flow values for each conduit.

    Args:
        input_file (str): Path to the INP file.
        sim_preconfig (SimulationPreconfig): Optional simulation preconfiguration object
        containing parameters updated for the simulation.
        step_advance (int): Time step in seconds to advance the simulation at each step. Default is 5 minutes.
    Returns:
        dict: Dictionary with conduit IDs as keys and accumulated flow values as values.
    """
    with Simulation(input_file, sim_preconfig=sim_preconfig) as sim:
        if conduits is None:
            conduits = list(Links(sim))
        conduit_flows = {conduit.linkid: 0 for conduit in conduits}
        # Set the time interval between simulation steps
        sim.step_advance(step_advance)
        for step in sim:
            for conduit in conduits:
                conduit_flows[conduit.linkid] += abs(conduit.flow)

    return conduit_flows


def get_conduits_from_input_file(input_file):
    """
    Get a dict of conduits and their heights from the INP file.

    Args:
        input_file (str): Path to the INP file.

    Returns:
        dict: Dictionary with conduit IDs as keys and their heights as values.
    """
    input = read_inp_file(input_file)
    conduits = {}
    for conduit in input.CONDUITS:
        if conduit not in conduits:
            conduits[conduit] = input.XSECTIONS[conduit]['height']
    return conduits


def change_height(input_file, conduit_name, ratio):
    """
    Change the height of the specified conduit by a given ratio.

    Args:
        input_file (str): Path to the INP file.
        conduit_name (str): The name of the conduit to change.
        ratio (float): The ratio by which to change the height.

    Returns:
        str: The path to the new INP file with the updated height.
    """
    input = read_inp_file(input_file)
    height_val = input.XSECTIONS[conduit_name]['height']
    new_value = height_val * ratio
    input.XSECTIONS[conduit_name]['height'] = new_value
    new_name = f'{input_file[:-4]}_conduit_{conduit_name}_height_{new_value:.4f}.inp'
    input.write_file(new_name)
    return new_name


def get_coordinates_from_input_file(input_file):
    """
    Get a dicts of links and their coordinates and
    nodes and their coordinates from the INP file.

    Args:
        input_file (str): Path to the INP file.

    Returns:
        dict: Dictionary with conduit IDs as keys and their coordinates as values.
        dict: Dictionary with node IDs as keys and their coordinates as values.
    """

    input = read_inp_file(input_file)
    # Create empty dicts to store node and link data
    nodes_coord = {}
    # Get nodes coordinates from INP [COORDINATES] section
    for node in input.COORDINATES:
        if node not in nodes_coord:
            coord = input.COORDINATES[node]
            nodes_coord[node] = Point(coord['x'], coord['y'])


    # Get links inlet and outlet nodes from INP.
    # Get coordinates of inlet and outlet nodes from nodes_coord.
    links_coord = {}
    for link in input.CONDUITS:
        if link not in links_coord:
            link_data = input.CONDUITS[link]
            inlet = link_data['from_node']
            outlet = link_data['to_node']
            if inlet in nodes_coord and outlet in nodes_coord:
                links_coord[link] = {
                    'inlet': nodes_coord[inlet],
                    'outlet': nodes_coord[outlet]
                }
    # Check if orifices section is present
    if 'ORIFICES' in input.keys():
        for link in input.ORIFICES:
            if link not in links_coord:
                link_data = input.ORIFICES[link]
                inlet = link_data['from_node']
                outlet = link_data['to_node']
                if inlet in nodes_coord and outlet in nodes_coord:
                    links_coord[link] = {
                        'inlet': nodes_coord[inlet],
                        'outlet': nodes_coord[outlet]
                    }

    return links_coord, nodes_coord