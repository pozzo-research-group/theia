# Example usage for parsing SAXS and UVVIS data into single NeXus file
nexus_parse converts SAXS nexus files and UVVis txt files into single NeXus format file following the NXcanSAS and NXoptical_spectroscopy standards.

### Command Line Interface

```bash
# Create combined SAXS + UV-Vis file
python3 nexus_parse.py input_saxs.nxs input_uvvis.txt output_combined.nxs

# Create SAXS-only file
python3 nexus_parse.py --saxs-only input.nxs saxs_only.nxs
```
## Dependencies

- h5py >= 3.0.0
- nexusformat 
    - use latest version available on github, pip and conda install versions not up to date enough for NXfabrication base class support