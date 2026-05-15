# HI Criticality Analysis

Code for the paper: **"Physics-Informed Criticality Analysis for Infrastructure Networks"**

> Nurit Klimovitsky-Maor, Lukas Guericke, Nicolas Caradot, Ofek Aloni, Shai
Kendler, Barak Fishbain. *[JOURNAL NAME]*, [YEAR]. DOI: [DOI]

---

## Overview

This repository implements a Machine Education based framework for assessing component-level criticality in physical Infrastructure Networks. A physics-based simulator (SWMM) acts as a *physical educator*, generating an augmented dataset by systematically degrading individual conduit capacities and observing the hydraulic consequences across the network. Three consequence measures (edge-specific flow, aggregate system flow, and network extent of disruption) are combined into a unified Hydraulically Informed (HI) criticality score using PCA and a polygon area method.

The method is demonstrated on urban sewer networks and evaluated against topological Edge Betweenness Centrality (EBC).

---

## Repository Structure

```
HI-criticality-analysis/
├── hydro_informed_generation.py   # Entry point: run simulations and analyze results
├── requirements.txt
└── src/
    ├── paths.py                   # Project-wide path configuration
    ├── __init__.py
    ├── simulation.py          # SWMM simulation and INP file utilities
    ├── data_processing.py     # Consequence measures, normalization, and scoring
    ├── utils.py               # File I/O and mathematical utilities
    ├── visualization.py       # Network risk map visualization
    └── Input/
        ├── Astlingen_SWMM.inp         # Astlingen benchmark (implementation by Sun et al., 2020)
        ├── 1Astlingen_Erft1.txt       # Rainfall time series (Astlingen)
        ├── 2Astlingen_Erft2.txt
        ├── 3Astlingen_Erft3.txt
        └── 4Astlingen_Erft4.txt
```

---

## Requirements

Python 3.9 or higher is recommended.

```bash
pip install -r requirements.txt
```

---

## Usage

All runs are configured and launched from `hydro_informed_generation.py`.

### Part 1 — Run simulations

Simulates capacity degradation scenarios for all conduits and saves raw results:

```python
run_simulations_main(case_name='Astlingen_SWMM')
```

This creates a timestamped output folder under `src/Results/` containing the raw per-conduit result CSVs.

For large networks, conduit subsets can be distributed across machines using the index range options in `run_simulations_main()`. See the comments in that function for details.

### Part 2 — Analyze results

Once all simulations are complete, compute and visualize the HI criticality scores:

```python
analyze_results_main(output_folder, case_name='Astlingen_SWMM')
```

Where `output_folder` is the path to the timestamped folder produced in Part 1.

---

## Data

**Astlingen** runs out of the box. It is a publicly available synthetic benchmark network (Schütze et al., 2018; Sun et al., 2020) and all required files are included.

SIT (Suburban Israeli Town) and SEC (Section of a large European City) are based on proprietary municipal GIS data and cannot be distributed. To apply the pipeline to your own network, add files to Input/ folder with your own SWMM model and update case_name accordingly in hydro_informed_generation.py.

## Citation

If you use this code in your work, please cite:

```bibtex
@article{[CITATION_KEY],
  author  = {[AUTHORS]},
  title   = {[PAPER TITLE]},
  journal = {[JOURNAL NAME]},
  year    = {[YEAR]},
  volume  = {[VOLUME]},
  pages   = {[PAGES]},
  doi     = {[DOI]}
}
```

---

## License

