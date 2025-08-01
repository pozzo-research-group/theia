# Theia
Plugin and tools for inputing SAXS experiment files into NOMAD Oasis.

## nexus_parser
Python module for parsing SAXS and UV-Vis spectroscopy data into NeXus format files following the NXcanSAS and NXoptical_spectroscopy standards.

### Command Line Interface

```bash
# Create combined SAXS + UV-Vis file
python3 nexus_parse.py input_saxs.nxs input_uvvis.txt output_combined.nxs

# Create SAXS-only file
python3 nexus_parse.py --saxs-only input.nxs saxs_only.nxs
```
### Dependencies

- h5py >= 3.0.0
- nexusformat 
    - use latest version available on github, pip and conda install versions not up to date enough for NXfabrication base class support

## nomad_theia_plugin
still underdevelopment