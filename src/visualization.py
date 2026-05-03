"""Contains all plotting and visualization functions"""

import matplotlib.pyplot as plt
import numpy as np
import os

from src.simulation import get_coordinates_from_input_file
from src.utils import get_angle_between_points

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import plotly.express as px
import plotly.graph_objects as go


def create_radar_plot(ax, accum_sums):
    """
    Create a radar plot for the normalized accumulated flow values.

    Args:
        ax: The axis to plot the radar chart on.
        accum_sums (DataFrame): DataFrame with accumulated flow values.
    """
    categories = ['Accumulated Flow', 'Specific Conduit Flow', 'Unaffected Conduits']
    num_vars = len(categories)

    # Compute angle for each axis
    angles = get_angle_between_points(num_vars)

    # Draw one axe per variable and add labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)

    # Draw ylabels
    ax.set_rlabel_position(0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", size=7)
    ax.set_ylim(0, 1)

    # Plot data
    values = accum_sums[
        ['norm_accum_flow_sum', 'norm_specific_conduit_flow_sum', 'unaffected_conduits_ratio']].mean().tolist()
    values += values[:1]
    ax.plot(angles, values, linewidth=2, linestyle='solid')
    ax.fill(angles, values, 'b', alpha=0.1)

    # Add annotations
    for i, value in enumerate(values[:-1]):
        angle_rad = angles[i]
        ax.annotate(f'{value:.2f}', xy=(angle_rad, value), xytext=(angle_rad, value + 0.1),
                    textcoords='data', ha='center', va='center', fontsize=10, color='black')


def define_basic_ratio_chart_params(ax, x, title):
    """
    Plot a chart with the given parameters.

    Args:
        ax: The axis to plot on.
        x (list): Ratios.
        title (str): Title of the plot.
    """
    ax.set_title(title)
    ax.set_xlabel('Ratio')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.set_xticks(x)
    ax.tick_params(axis='x', rotation=45)


def plot_accumulated_flows(accum_sums, conduit, output_folder):
    """
    Plot the accumulated flow values and the flow values of the specific conduit.

    Args:
        accum_sums (DataFrame): DataFrame with accumulated flow values.
        conduit (str): The name of the conduit.
        output_folder (str): The path to the output folder.
    """
    fig, ((ax1, ax2), (ax3, ax4), (ax5, ax6)) = plt.subplots(3, 2, figsize=(30, 30))
    # main title
    fig.suptitle(f'Accumulated Flow Values for Conduit {conduit}', fontsize=16)

    ratios = accum_sums['ratio'].tolist()

    # Plot for accumulated flow values for all conduits
    define_basic_ratio_chart_params(ax1, ratios, 'All conduits')
    ax1.set_ylabel('Accumulated Flow in all conduits')
    ax1.plot(ratios, accum_sums['accum_flow_sum'], marker='o', color='blue')

    # Plot for accumulated flow values for all conduits with y-axis starting at 0
    define_basic_ratio_chart_params(ax2, ratios, 'All conduits (y-axis starts at 0)')
    ax2.set_ylabel('Accumulated Flow in all conduits')
    ax2.plot(ratios, accum_sums['accum_flow_sum'], marker='o', color='blue')
    ax2.set_ylim(bottom=0)

    # Plot for accumulated flow values of the specific conduit
    define_basic_ratio_chart_params(ax3, ratios, f'Accumulated flow in conduit {conduit}')
    ax3.set_ylabel('Flow Value')
    ax3.plot(ratios, accum_sums['specific_conduit_flow_sum'], marker='o', color='green')

    # Plot for normalized accumulated flow values
    define_basic_ratio_chart_params(ax4, ratios, 'Normalized Accumulated Flow Values')
    ax4.set_ylabel('Normalized Flow Value')
    ax4.plot(ratios, accum_sums['norm_accum_flow_sum'], marker='o', color='blue', label='All conduits')
    ax4.plot(ratios, accum_sums['norm_specific_conduit_flow_sum'], marker='o', color='green',
             label=f'Conduit {conduit}')
    ax4.plot(ratios, accum_sums['unaffected_conduits_ratio'], marker='o', color='red',
             label='Unaffected conduits')
    ax4.legend()

    # Plot for number of affected conduits
    define_basic_ratio_chart_params(ax5, ratios, 'Number of Affected Conduits')
    ax5.set_ylabel('Number of Affected Conduits')
    ax5.plot(ratios, accum_sums['affected_conduits'], marker='o', color='red')

    # Remove the existing axis before creating a new one
    if ax6:
        ax6.remove()

    # Radar plot
    ax6 = plt.subplot(3, 2, 6, polar=True)
    ax6.set_title('Radar Plot of Normalized Values')
    create_radar_plot(ax6, accum_sums)

    plt.tight_layout()

    # Save the plot to the output folder
    plot_filename = os.path.join(output_folder, f'plot_{conduit}_accumulated_flows.png')
    plt.savefig(plot_filename)
    plt.close(fig)


def plot_scatter_normalized_flows(ratio_sums, output_folder, risk_colors=False):
    """
    Plot a scatter plot with risk visualizations using background colors.

    Args:
        ratio_sums (DataFrame): DataFrame with normalized flow values.
        output_folder (str): The path to the output folder.
        risk_colors (bool): If True, use risk colors for background visualization.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Scatter plot
    ax.scatter(ratio_sums['norm_accum_flow_sum'], ratio_sums['norm_specific_conduit_flow_sum'], color='blue',
               marker='o')
    ax.set_title('Normalized Accumulated Flow Values with Resilience Visualization')
    ax.set_xlabel('Sum of accumulated flow in all conduits')
    ax.set_ylabel('Accumulated flow in conduit')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Annotate each point with the conduit name
    for i, row in ratio_sums.iterrows():
        ax.annotate(row['conduit'], (row['norm_accum_flow_sum'], row['norm_specific_conduit_flow_sum']), fontsize=9,
                    ha='right')

    if risk_colors:
        # Define the risk levels and colors
        risk_colors = [
            ['lightcoral', 'lightcoral', 'orange'],
            ['lightcoral', 'orange', 'lightgreen'],
            ['orange', 'lightgreen', 'lightgreen']
        ]

        # Define the split points
        x_split = np.linspace(0, 1, 4)
        y_split = np.linspace(0, 1, 4)

        # Add background colors
        for i in range(3):
            for j in range(3):
                ax.axvspan(x_split[i], x_split[i + 1], ymin=y_split[j], ymax=y_split[j + 1], color=risk_colors[j][i],
                           alpha=0.3)

    # Save the plot to the output folder
    plot_filename = os.path.join(output_folder, 'scatter_normalized_flows_with_Resilience.png')
    plt.savefig(plot_filename)
    #plt.show()
    plt.close(fig)


def plot_1d_risk_visualization(conduits_risk, output_folder, score_name= 'Polygon_Area'):
    """
    Plot a 1D colorbar risk visualization based on the risk values.

    Args:
        conduits_risk (dict): Dictionary with conduit names and normalized score values.
        output_folder (str): The path to the output folder.
    """

    # Create the figure and axis
    # dynamic figsize based on number of conduits
    dyn_size = len(conduits_risk) // 200 + 10
    fig, ax = plt.subplots(figsize=(dyn_size*5, dyn_size))

    # Plot each conduit as a point on the color scale
    for i, (conduit_name, risk_score) in enumerate(conduits_risk.items()):
        ax.scatter(
            risk_score, 0.5,
            color=plt.cm.RdYlGn(risk_score),  # Red to green color scale
            s=100, label=conduit_name
        )
        # Adjust the vertical position of the labels to avoid overlap
        # Alternate label positions
        if i % 8 == 0:
            y_offset = 0.6  # Above position 1
        elif i % 8 == 1:
            y_offset = 0.35 # Below position 1
        elif i % 8 == 2:
            y_offset = 0.7  # Above position 2
        elif i % 8 == 3:
            y_offset = 0.25  # Below position 2
        elif i % 8 == 4:
            y_offset = 0.8  # Above position 3
        elif i % 8 == 5:
            y_offset = 0.15  # Below position 3
        elif i % 8 == 6:
            y_offset = 0.9 # Above position 4
        else:
            y_offset = 0.05  # Below position 4

        ax.text(
            risk_score, y_offset,
            conduit_name, ha='center', va='bottom', fontsize=9, rotation=45
        )

    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap='RdYlGn', norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='horizontal', pad=0.1, shrink=0.4)
    cbar.set_label('Normalized Resilience')

    # Set axis limits and labels
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xlabel(f'Score: {score_name}')
    ax.set_title('1D Resilience Visualization of Conduits')

    # Save the plot to the output folder
    plot_filename = os.path.join(output_folder, f'{score_name}_1d_Resilience_visualization.png')
    plt.savefig(plot_filename)
    #plt.show()
    plt.close(fig)


def visualize_risk_on_network(risk_data, input_file, output_folder, score_name='Score'):
    """
    Visualize risk levels by coloring conduits on a simplified network map.

    Args:
        risk_data (dict): Dictionary containing conduit IDs and their risk scores.
        input_file (str): Path to the INP file.
        output_folder (str): The path to save the visualization.
    """
    conduits_coord, nodes_coord = get_coordinates_from_input_file(input_file)

    # Create GeoDataFrame for conduits with risk data
    conduits_data = []
    for conduit_id, coords in conduits_coord.items():
        # Create a line between inlet and outlet
        line = LineString([
            (coords['inlet'].x, coords['inlet'].y),
            (coords['outlet'].x, coords['outlet'].y)
        ])

        # Check if risk data is available for this conduit
        has_risk_data = conduit_id in risk_data.keys()
        # Get risk score (which is already normalized) or None if not available
        risk_score = risk_data.get(conduit_id, None)

        conduits_data.append({
            'id': conduit_id,
            'risk_score': risk_score,
            'has_risk_data': has_risk_data,
            'geometry': line
        })

    conduits_gdf = gpd.GeoDataFrame(conduits_data, crs="EPSG:4326")

    # Interactive plot using Plotly
    fig = go.Figure()
    colorscale = px.colors.diverging.RdYlGn

    # Add nodes (points)
    node_x = [point.x for point in nodes_coord.values()]
    node_y = [point.y for point in nodes_coord.values()]
    node_text = [f"Node: {node}" for node in nodes_coord.keys()]

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        marker=dict(size=10, color='blue', line=dict(width=2, color='darkblue')),
        name='Nodes',
        hoverinfo='text',
        text=node_text,
        showlegend=False
    ))

    # Add conduits (lines) with color based on risk score
    for _, conduit in conduits_gdf.iterrows():
        x = [conduit.geometry.coords[0][0], conduit.geometry.coords[1][0]]
        y = [conduit.geometry.coords[0][1], conduit.geometry.coords[1][1]]

        # Calculate midpoint coordinates
        mid_x = (x[0] + x[1]) / 2
        mid_y = (y[0] + y[1]) / 2

        # Different color for conduits with missing risk data
        if not conduit['has_risk_data']:
            color = 'rgb(150, 150, 150)'  # Gray for missing data
            hover_text = f"Conduit ID: {conduit['id']}<br>Resilience Score: No Data"
        else:
            color = px.colors.sample_colorscale(colorscale, [conduit['risk_score']])[0]
            hover_text = f"Conduit ID: {conduit['id']}<br>Resilience Score: {conduit['risk_score']:.2f}"

        # Add the visible line WITH hover capability
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode='lines',
            line=dict(width=5, color=color),  # Slightly thicker line
            name=f"Conduit {conduit['id']}",
            hoverinfo='text',
            text=hover_text,
            showlegend=False
        ))

        # Add transparent marker at the midpoint with the same hover text
        fig.add_trace(go.Scatter(
            x=[mid_x], y=[mid_y],
            mode='markers',
            marker=dict(
                size=15,  # Larger size to make it easier to hover
                color='rgba(0,0,0,0)',  # Completely transparent
                opacity=0  # Redundant but ensures transparency
            ),
            hoverinfo='text',
            text=hover_text,
            showlegend=False
        ))

    # Create a colorbar for risk levels
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(
            colorscale=[
                [0, 'red'],
                [0.5, 'yellow'],
                [1, 'green']
            ],
            showscale=True,
            colorbar=dict(
                title='Resilience Score',
                tickvals=[0, 0.5, 1],
                ticktext=["0.0", "0.5", "1.0"]
            ),
            cmin=0,
            cmax=1
        ),
        showlegend=False
    ))

    # Update layout
    fig.update_layout(
        title=f'Network Resilience Visualization ({score_name})',
        xaxis_title='Longitude',
        yaxis_title='Latitude',
        autosize=True,
        height=600,
        width=1200,
        hovermode='closest',
        hoverdistance=10,
        spikedistance=1000,  # Distance to show spike
        hoverlabel=dict(
            bgcolor='white',
            font_size=12,
            font_family='Arial, sans-serif'
        ),
        margin=dict(t=50, b=50, l=50, r=50),
        plot_bgcolor='rgba(240, 240, 240, 0.2)'
    )

    # Save as HTML file
    output_file = os.path.join(output_folder, f'{score_name}_conduit_Resilience_map.html')
    fig.write_html(output_file)

    # Also save as static image
    static_file = os.path.join(output_folder, f'{score_name}_conduit_Resilience_map.png')
    fig.write_image(static_file)

    return fig  # Return figure for potential further use or display

def visualize_risk(risk_scores, input_file, output_folder, score_name='Score'):
    """
    Visualize risk scores on a 1D plot and on a network map.
    Args:
        risk_data (dict): Dictionary containing conduit IDs and their risk scores.
        input_file (str): Path to the INP file.
        output_folder (str): The path to save the visualization.
    """
    # Plot 1D risk visualization
    plot_1d_risk_visualization(risk_scores, output_folder, score_name)

    # Create a map of all conduits and add colors to conduits with score
    visualize_risk_on_network(risk_scores, input_file, output_folder, score_name)


def create_plots_for_conduits(conduits_to_plot, raw_results_folder, output_folder):
    """
    Create plots for specified conduits based on their accumulated flow data in CSV files.
    Args:
        conduits_to_plot (list): List of conduit IDs to plot.
        raw_results_folder (str): Path to the folder containing raw results CSV files.
        output_folder (str): Path to the folder where plots will be saved.
    """
    print(f"Conduits to plot: {conduits_to_plot}")

    for conduit in conduits_to_plot:
        # Read conduit data from csv
        conduit_path = os.path.join(raw_results_folder, f'conduit_{conduit}_results.csv')
        conduit_data = pd.read_csv(conduit_path)
        plot_accumulated_flows(conduit_data, conduit, output_folder)

