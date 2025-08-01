from datetime import datetime

import h5py
import numpy as np
from nexusformat.nexus import (
    NXbeam,
    NXcollection,
    NXcomponent,
    NXdata,
    NXdetector,
    NXentry,
    NXenvironment,
    NXfabrication,
    NXfield,
    NXinstrument,
    NXmonochromator,
    NXnote,
    NXprocess,
    NXroot,
    NXsample,
    NXsource,
    NXuser,
)


def parse_uvvis_file(file_path):  # noqa: PLR0912, PLR0915
    """
    Parse UV-vis absorbance file and extract metadata and spectral data.
    
    Args:
        file_path: Path to the UV-vis absorbance file
        
    Returns:
        tuple: (metadata_dict, wavelength_array, absorbance_array)
    """
    metadata = {}
    wavelengths = []
    absorbances = []
    
    with open(file_path, 'r') as f:  # noqa: UP015
        lines = f.readlines()
    
    # Parse header metadata
    in_spectral_data = False
    
    for line in lines:
        line = line.strip()  # noqa: PLW2901
        
        if line.startswith('>>>>>Begin Spectral Data<<<<<'):
            in_spectral_data = True
            continue
            
        if not in_spectral_data:
            # Parse metadata from header
            if line.startswith('Date:'):
                # Extract date and time
                date_str = line.replace('Date:', '').strip()
                # Parse date like "Thu Jul 03 16:12:06 PDT 2025"
                try:
                    # Remove day of week and timezone for simpler parsing
                    date_parts = date_str.split()
                    if len(date_parts) >= 5:
                        # Reconstruct as "Jul 03 16:12:06 2025"
                        date_clean = f"{date_parts[1]} {date_parts[2]} {date_parts[3]} {date_parts[5]}"
                        parsed_date = datetime.strptime(date_clean, "%b %d %H:%M:%S %Y")
                        metadata['start_time'] = parsed_date.isoformat()
                        metadata['end_time'] = parsed_date.isoformat()  # Assume instantaneous measurement
                except:  # noqa: E722
                    metadata['start_time'] = date_str
                    metadata['end_time'] = date_str
                    
            elif line.startswith('User:'):
                metadata['user'] = line.replace('User:', '').strip()
            elif line.startswith('Spectrometer:'):
                metadata['spectrometer'] = line.replace('Spectrometer:', '').strip()
            elif line.startswith('Trigger mode:'):
                metadata['trigger_mode'] = int(line.replace('Trigger mode:', '').strip())
            elif line.startswith('Integration Time (sec):'):
                metadata['integration_time'] = float(line.replace('Integration Time (sec):', '').strip())
            elif line.startswith('Scans to average:'):
                metadata['scans_to_average'] = int(line.replace('Scans to average:', '').strip())
            elif line.startswith('Nonlinearity correction enabled:'):
                metadata['nonlinearity_correction'] = line.replace('Nonlinearity correction enabled:', '').strip().lower() == 'true'
            elif line.startswith('Boxcar width:'):
                metadata['boxcar_width'] = int(line.replace('Boxcar width:', '').strip())
            elif line.startswith('Storing dark spectrum:'):
                metadata['storing_dark_spectrum'] = line.replace('Storing dark spectrum:', '').strip().lower() == 'true'
            elif line.startswith('XAxis mode:'):
                metadata['xaxis_mode'] = line.replace('XAxis mode:', '').strip()
            elif line.startswith('Number of Pixels in Spectrum:'):
                metadata['number_of_pixels'] = int(line.replace('Number of Pixels in Spectrum:', '').strip())
        else:  # noqa: PLR5501
            # Parse spectral data
            if line and not line.startswith('>'):
                try:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        wavelength = float(parts[0])
                        absorbance = float(parts[1])
                        wavelengths.append(wavelength)
                        absorbances.append(absorbance)
                except ValueError:
                    continue
    
    return metadata, np.array(wavelengths), np.array(absorbances)

def create_uvvis_entry(metadata, wavelengths, absorbances):  # noqa: PLR0912, PLR0915
    """
    Create an NXoptical_spectroscopy-compliant HDF5 file from UV-vis data using h5py.
    
    Args:
        metadata: Dictionary of metadata
        wavelengths: Array of wavelengths
        absorbances: Array of absorbance values
        
    Returns:
        NXentry object following NXuvvis structure
    """
        # Create main entry
    entry = NXentry()
    entry.attrs['NX_class'] = 'NXentry'
    
    # Required definition field
    entry.definition = NXfield('NXoptical_spectroscopy', name='definition')
    entry.definition.attrs['version'] = '1.0'
    entry.definition.attrs['URL'] = 'https://github.com/FAIRmat-NFDI/nexus_definitions/'
    
    # Entry metadata
    entry.title = NXfield('UV-Vis Absorbance Spectroscopy Measurement', name='title')
    entry.experiment_type = NXfield('transmission spectroscopy', name='experiment_type')
    
    if 'start_time' in metadata:
        entry.start_time = NXfield(metadata['start_time'], name='start_time')
    if 'end_time' in metadata:
        entry.end_time = NXfield(metadata['end_time'], name='end_time')
    
        # User information
    if 'user' in metadata:
        user = NXuser()
        user.attrs['NX_class'] = 'NXuser'
        user.name = NXfield(metadata['user'], name='name')
        entry.user = user
    
    # Create instrument group
    instrument = NXinstrument()
    instrument.attrs['NX_class'] = 'NXinstrument'
    
    # Add angle reference frame (required field)
    instrument.angle_reference_frame = NXfield('beam centered', name='angle_reference_frame')
    
    # Source information
    source = NXsource()
    source.attrs['NX_class'] = 'NXsource'
    source.type = NXfield('Broadband Tunable Light Source', name='type')
    if 'spectrometer' in metadata:
        source.name = NXfield(f"Light source of {metadata['spectrometer']}", name='name')
    source.associated_beam = NXfield('/entry/instrument/beam_incident', name='associated_beam')
    
    # Device information for source
    source_device_info = NXfabrication()
    source_device_info.attrs['NX_class'] = 'NXfabrication'
    if 'spectrometer' in metadata:
        source_device_info.model = NXfield(metadata['spectrometer'], name='model')
    source.device_information = source_device_info

    instrument.source = source
    
    # Incident beam
    beam_incident = NXbeam()
    beam_incident.attrs['NX_class'] = 'NXbeam'
    beam_incident.parameter_reliability = NXfield('nominal', name='parameter_reliability')
    beam_incident.associated_source = NXfield('/entry/instrument/source', name='associated_source')
    # Add wavelength range based on data
    beam_incident.incident_wavelength = NXfield(np.mean(wavelengths), name='incident_wavelength', units='nm')
    beam_incident.incident_wavelength_spread = NXfield(np.max(wavelengths) - np.min(wavelengths), 
                                                      name='incident_wavelength_spread', units='nm')
    
    instrument.beam_incident = beam_incident
    
    # Detector
    detector = NXdetector()
    detector.attrs['NX_class'] = 'NXdetector'
    detector.detector_channel_type = NXfield('multichannel', name='detector_channel_type')
    detector.detector_type = NXfield('CCD', name='detector_type')  # Assumption for spectrometer
    
    # Raw data group
    raw_data = NXdata()
    raw_data.attrs['NX_class'] = 'NXdata'
    raw_data.attrs['signal'] = 'raw'
    raw_data.raw = NXfield(absorbances, name='raw')
    raw_data.wavelength = NXfield(wavelengths, name='wavelength', units='nm')
    raw_data.attrs['axes'] = ['wavelength']
    detector.raw_data = raw_data

    # Detector device information
    detector_device_info = NXfabrication()
    detector_device_info.attrs['NX_class'] = 'NXfabrication'
    if 'spectrometer' in metadata:
        detector_device_info.model = NXfield(metadata['spectrometer'], name='model')
    detector.device_information = detector_device_info
    
    instrument.detector = detector
    
    # Monochromator (part of spectrometer)
    monochromator = NXmonochromator()
    monochromator.attrs['NX_class'] = 'NXmonochromator'
    
    mono_device_info = NXfabrication()
    mono_device_info.attrs['NX_class'] = 'NXfabrication'
    if 'spectrometer' in metadata:
        mono_device_info.model = NXfield(metadata['spectrometer'], name='model')
    monochromator.device_information = mono_device_info
    
    instrument.monochromator = monochromator
    
    # Add instrument-specific metadata not in standard schema
    if any(key in metadata for key in ['trigger_mode', 'integration_time', 'scans_to_average', 
                                      'nonlinearity_correction', 'boxcar_width', 'storing_dark_spectrum',
                                      'xaxis_mode', 'number_of_pixels']):

        # Create custom component for spectrometer-specific settings
        spectrometer_settings = NXcomponent()
        spectrometer_settings.attrs['NX_class'] = 'NXcomponent'
        spectrometer_settings.attrs['component_type'] = 'spectrometer_settings'
        
        if 'trigger_mode' in metadata:
            spectrometer_settings.trigger_mode = NXfield(metadata['trigger_mode'], name='trigger_mode')
        if 'integration_time' in metadata:
            spectrometer_settings.integration_time = NXfield(metadata['integration_time'], 
                                                            name='integration_time', units='s')
        if 'scans_to_average' in metadata:
            spectrometer_settings.scans_to_average = NXfield(metadata['scans_to_average'], name='scans_to_average')
        if 'nonlinearity_correction' in metadata:
            spectrometer_settings.nonlinearity_correction_enabled = NXfield(metadata['nonlinearity_correction'], 
                                                                           name='nonlinearity_correction_enabled')
        if 'boxcar_width' in metadata:
            spectrometer_settings.boxcar_width = NXfield(metadata['boxcar_width'], name='boxcar_width')
        if 'storing_dark_spectrum' in metadata:
            spectrometer_settings.storing_dark_spectrum = NXfield(metadata['storing_dark_spectrum'], 
                                                                 name='storing_dark_spectrum')
        if 'xaxis_mode' in metadata:
            spectrometer_settings.xaxis_mode = NXfield(metadata['xaxis_mode'], name='xaxis_mode')
        if 'number_of_pixels' in metadata:
            spectrometer_settings.number_of_pixels = NXfield(metadata['number_of_pixels'], name='number_of_pixels')
        
        instrument.spectrometer_settings = spectrometer_settings
    
    # Overall instrument device information
    instrument_device_info = NXfabrication()
    instrument_device_info.attrs['NX_class'] = 'NXfabrication'
    if 'spectrometer' in metadata:
        instrument_device_info.model = NXfield(metadata['spectrometer'], name='model')
    instrument.device_information = instrument_device_info
    
    entry.instrument = instrument
    
    # Sample information
    sample = NXsample()
    sample.attrs['NX_class'] = 'NXsample'
    sample.name = NXfield('Unknown Sample', name='name')
    sample.sample_id = NXfield('UV-Vis-001', name='sample_id')
    sample.physical_form = NXfield('unknown', name='physical_form')
    sample.description = NXfield('UV-Vis absorbance measurement sample', name='description')
    
    # Sample environment
    sample_env = NXenvironment()
    sample_env.attrs['NX_class'] = 'NXenvironment'
    sample_env.sample_medium = NXfield('air', name='sample_medium')
    sample.environment = sample_env

    entry.sample = sample
    
    # Main data group (required)
    data = NXdata()
    data.attrs['NX_class'] = 'NXdata'
    data.attrs['signal'] = 'absorbance'
    data.attrs['axes'] = ['wavelength']
    
    data.wavelength = NXfield(wavelengths, name='wavelength', units='nm')
    data.absorbance = NXfield(absorbances, name='absorbance', units='a.u.')
    data.wavelength.attrs['long_name'] = 'Wavelength'
    data.absorbance.attrs['long_name'] = 'Absorbance'
    
    entry.data = data
    
    # Add source file information as additional metadata
    if 'source_filename' in metadata:
        entry.source_file_info = NXfield(metadata['source_filename'], name='source_file_info')
    
    return entry

def copy_group_recursive(src_group, dest_parent, group_name):  # noqa: PLR0912
    """
    Recursively copy a group from source to destination, preserving structure and attributes.
    
    Args:
        src_group: Source h5py group
        dest_parent: Destination parent group (nexusformat object)
        group_name: Name for the new group
    """
    # Create the destination group
    if hasattr(dest_parent, group_name):
        dest_group = getattr(dest_parent, group_name)
    else:
        if 'NX_class' in src_group.attrs:
            nx_class = src_group.attrs['NX_class'].decode() if isinstance(src_group.attrs['NX_class'], bytes) else src_group.attrs['NX_class']
            
            # Create appropriate NX object based on class
            if nx_class == 'NXprocess':
                dest_group = NXprocess()
            elif nx_class == 'NXnote':
                dest_group = NXnote()
            elif nx_class == 'NXcollection':
                dest_group = NXcollection()
            elif nx_class == 'NXdata':
                dest_group = NXdata()
            else:
                # Generic group
                from nexusformat.nexus import NXgroup
                dest_group = NXgroup()
        else:
            from nexusformat.nexus import NXgroup
            dest_group = NXgroup()
        
        setattr(dest_parent, group_name, dest_group)
    
    # Copy all attributes
    for attr_name, attr_value in src_group.attrs.items():
        if isinstance(attr_value, bytes):
            try:
                attr_value = attr_value.decode('utf-8')  # noqa: PLW2901
            except UnicodeDecodeError:
                pass  # Keep as bytes if decode fails
        dest_group.attrs[attr_name] = attr_value
    
    # Copy datasets and recurse into subgroups
    for item_name, item in src_group.items():
        if isinstance(item, h5py.Dataset):
            # Copy dataset
            data = item[()]
            # Handle string datasets
            if item.dtype.kind in ['S', 'U', 'O']:
                if isinstance(data, bytes):
                    try:
                        data = data.decode('utf-8')
                    except UnicodeDecodeError:
                        pass
                elif isinstance(data, np.ndarray) and data.dtype.kind == 'S':
                    try:
                        data = np.array([x.decode('utf-8') if isinstance(x, bytes) else x for x in data.flat]).reshape(data.shape)
                    except UnicodeDecodeError:
                        pass
            
            field = NXfield(data, name=item_name)
            
            # Copy dataset attributes
            for attr_name, attr_value in item.attrs.items():
                if isinstance(attr_value, bytes):
                    try:
                        attr_value = attr_value.decode('utf-8')  # noqa: PLW2901
                    except UnicodeDecodeError:
                        pass
                field.attrs[attr_name] = attr_value
            
            setattr(dest_group, item_name, field)
            
        elif isinstance(item, h5py.Group):
            # Recursively copy subgroup
            copy_group_recursive(item, dest_group, item_name)

def parse_create_saxs_entry(input_file):  # noqa: PLR0915
    # === Read from the original SAXS file ===
    with h5py.File(input_file, 'r') as f:
        q = f['/processed/result/q'][()]
        I = f['/processed/result/data'][()].squeeze()  # noqa: E741
        Ierr = f['/processed/result/errors'][()].squeeze()

        # === Create NXcanSAS layout ===
        # NXcanSAS requires an NXentry -> NXdata hierarchy
        saxs_entry = NXentry()
        saxs_entry.attrs['NX_class'] = 'NXentry'
        saxs_entry.attrs['definition'] = 'NXcanSAS'
        saxs_entry.attrs['canSAS_class'] = 'SASentry'

        # Main SAXS data group (required by NXcanSAS)
        data_group = NXdata()
        data_group.attrs['NX_class'] = 'NXdata'
        data_group.attrs['canSAS_class'] = 'SASdata'
        data_group.I = NXfield(I, name='I', units='a.u.')
        data_group.Q = NXfield(q, name='Q', units='1/angstrom')
        data_group.Idev = NXfield(Ierr, name='Idev', units='a.u.')

        # Optional: associate axes
        data_group.attrs['axes'] = ['Q']
        data_group.attrs['signal'] = 'I'
        data_group.attrs['I_uncertainty'] = 'Idev'
        data_group['I'].attrs['uncertainties'] = 'Idev'
        data_group.attrs['Q_indices'] = 0
        data_group.attrs['I_axes'] = 'Q'

        saxs_entry.data = data_group

        # === Copy process information ===
        if '/processed/process' in f:
            print("Copying process information...")
            copy_group_recursive(f['/processed/process'], saxs_entry, 'process')
        
        # === Copy auxiliary data (NXcollection groups) ===
        if '/processed/auxiliary' in f:
            print("Copying auxiliary data...")
            copy_group_recursive(f['/processed/auxiliary'], saxs_entry, 'auxiliary')
        
        # === Copy intermediate processing results ===
        if '/processed/intermediate' in f:
            print("Copying intermediate processing results...")
            copy_group_recursive(f['/processed/intermediate'], saxs_entry, 'intermediate')
        
        # === Add processing notes for NXcanSAS compliance ===
        # NXcanSAS allows additional NXnote groups for processing information
        if hasattr(saxs_entry, 'process'):
            # Add a summary note about the processing
            processing_summary = NXnote()
            processing_summary.attrs['NX_class'] = 'NXnote'
            processing_summary.attrs['canSAS_class'] = 'SASprocessnote'
            
            # Extract processing information from the copied process group
            try:
                if hasattr(saxs_entry.process, 'program') and hasattr(saxs_entry.process, 'version'):
                    program = str(saxs_entry.process.program.nxdata)
                    version = str(saxs_entry.process.version.nxdata)
                    processing_summary.description = NXfield(
                        f"Data processed with {program} version {version}",
                        name='description'
                    )
                
                if hasattr(saxs_entry.process, 'date'):
                    processing_summary.date = NXfield(
                        str(saxs_entry.process.date.nxdata),
                        name='date'
                    )
            except Exception as e:
                print(f"Warning: Could not extract processing summary: {e}")
                processing_summary.description = NXfield(
                    "SAXS data processing completed",
                    name='description'
                )
            
            saxs_entry.processing_note = processing_summary

        # === Add metadata about data provenance ===
        # This helps with traceability while maintaining NXcanSAS structure
        provenance = NXnote()
        provenance.attrs['NX_class'] = 'NXnote'
        provenance.attrs['canSAS_class'] = 'SASprocessnote'
        provenance.source_file = NXfield(input_file, name='source_file')
        provenance.description = NXfield(
            "Converted from NeXus processed data to NXcanSAS format with full processing history",
            name='description'
        )
        saxs_entry.provenance = provenance

        return saxs_entry

def create_saxs_uvvis_nexus(saxs_entry, uvvis_entry):

    # Create a new NeXus root group
    root = NXroot()

    # Add SAXS entry
    root.saxs_entry = saxs_entry

    # Add UV-vis entry if successfully parsed
    if uvvis_entry is not None:
        root.uvvis_entry = uvvis_entry

    root.save(output_file)

def create_saxs_only_nexus(input_file, output_file, validate=True):  # noqa: PLR0915
    """
    Create a NeXus file containing only SAXS data following NXcanSAS standard.
    
    Args:
        input_file (str): Path to the input processed SAXS file
        output_file (str): Path for the output NeXus file
        validate (bool): Whether to validate the created file
        
    Returns:
        dict: Results of the conversion process
    """
    try:
        with h5py.File(input_file, 'r') as f:
            # Read SAXS data
            q = f['/processed/result/q'][()]
            I = f['/processed/result/data'][()].squeeze()  # noqa: E741
            Ierr = f['/processed/result/errors'][()].squeeze()

            print("Loaded SAXS data:")
            print(f"  - Q points: {len(q)}")
            print(f"  - Q range: {q[0]:.6f} - {q[-1]:.6f} 1/Å")
            print(f"  - Intensity range: {I.min():.3e} - {I.max():.3e}")

            # === Create NXcanSAS layout ===
            saxs_entry = NXentry()
            saxs_entry.attrs['NX_class'] = 'NXentry'
            saxs_entry.attrs['definition'] = 'NXcanSAS'
            saxs_entry.attrs['canSAS_class'] = 'SASentry'

            # Main SAXS data group (required by NXcanSAS)
            data_group = NXdata()
            data_group.attrs['NX_class'] = 'NXdata'
            data_group.attrs['canSAS_class'] = 'SASdata'
            data_group.I = NXfield(I, name='I', units='a.u.')
            data_group.Q = NXfield(q, name='Q', units='1/angstrom')
            data_group.Idev = NXfield(Ierr, name='Idev', units='a.u.')

            # Associate axes
            data_group.attrs['axes'] = ['Q']
            data_group.attrs['signal'] = 'I'
            data_group.attrs['I_uncertainty'] = 'Idev'
            data_group['I'].attrs['uncertainties'] = 'Idev'
            data_group.attrs['Q_indices'] = 0
            data_group.attrs['I_axes'] = 'Q'

            saxs_entry.data = data_group

            # === Copy process information ===
            if '/processed/process' in f:
                print("Copying process information...")
                copy_group_recursive(f['/processed/process'], saxs_entry, 'process')
            
            # === Copy auxiliary data (NXcollection groups) ===
            if '/processed/auxiliary' in f:
                print("Copying auxiliary data...")
                copy_group_recursive(f['/processed/auxiliary'], saxs_entry, 'auxiliary')
            
            # === Copy intermediate processing results ===
            if '/processed/intermediate' in f:
                print("Copying intermediate processing results...")
                copy_group_recursive(f['/processed/intermediate'], saxs_entry, 'intermediate')
            
            # === Add processing notes for NXcanSAS compliance ===
            if hasattr(saxs_entry, 'process'):
                processing_summary = NXnote()
                processing_summary.attrs['NX_class'] = 'NXnote'
                processing_summary.attrs['canSAS_class'] = 'SASprocessnote'
                
                try:
                    if hasattr(saxs_entry.process, 'program') and hasattr(saxs_entry.process, 'version'):
                        program = str(saxs_entry.process.program.nxdata)
                        version = str(saxs_entry.process.version.nxdata)
                        processing_summary.description = NXfield(
                            f"Data processed with {program} version {version}",
                            name='description'
                        )
                    
                    if hasattr(saxs_entry.process, 'date'):
                        processing_summary.date = NXfield(
                            str(saxs_entry.process.date.nxdata),
                            name='date'
                        )
                except Exception as e:
                    print(f"Warning: Could not extract processing summary: {e}")
                    processing_summary.description = NXfield(
                        "SAXS data processing completed",
                        name='description'
                    )
                
                saxs_entry.processing_note = processing_summary

            # === Add metadata about data provenance ===
            provenance = NXnote()
            provenance.attrs['NX_class'] = 'NXnote'
            provenance.attrs['canSAS_class'] = 'SASprocessnote'
            provenance.source_file = NXfield(input_file, name='source_file')
            provenance.description = NXfield(
                "Converted from NeXus processed data to NXcanSAS format with full processing history",
                name='description'
            )
            saxs_entry.provenance = provenance

        # Create root and save
        root = NXroot()
        root.entry = saxs_entry

        # Save the file
        root.save(output_file)
        print(f"SAXS-only NeXus file saved to: {output_file}")

        results = {
            "success": True,
            "output_file": output_file,
            "q_points": len(q),
            "q_range": f"{q[0]:.6f} - {q[-1]:.6f} 1/Å",
            "intensity_range": f"{I.min():.3e} - {I.max():.3e}"
        }

        # Validate if requested
        if validate:
            validation = validate_saxs_nexus_file(output_file)
            results["validation"] = validation
            
            if validation["valid"]:
                print("✓ SAXS NeXus file validation passed")
            else:
                print("✗ SAXS NeXus file validation failed:")
                for error in validation["errors"]:
                    print(f"  - {error}")

        return results

    except Exception as e:
        return {"success": False, "error": str(e)}

def validate_saxs_nexus_file(nexus_file_path):  # noqa: PLR0912
    """
    Validate the structure of a SAXS NeXus file against NXcanSAS standard.
    
    Args:
        nexus_file_path (str): Path to the NeXus file to validate
        
    Returns:
        dict: Validation results
    """
    validation_results = {
        "valid": False,
        "errors": [],
        "structure": {}
    }
    
    try:
        with h5py.File(nexus_file_path, 'r') as f:
            # Check for required groups and fields for NXcanSAS
            required_structure = {
                'entry': {
                    'type': 'group',
                    'required_attrs': ['NX_class', 'definition', 'canSAS_class'],
                    'required_groups': ['data']
                },
                'entry/data': {
                    'type': 'group',
                    'required_attrs': ['NX_class', 'canSAS_class', 'signal', 'axes'],
                    'required_fields': ['I', 'Q', 'Idev']
                }
            }
            
            # Validate structure
            for path, requirements in required_structure.items():
                if path not in f:
                    validation_results["errors"].append(f"Missing required path: {path}")
                    continue
                
                obj = f[path]
                
                # Check attributes
                for attr in requirements.get('required_attrs', []):
                    if attr not in obj.attrs:
                        validation_results["errors"].append(f"Missing required attribute '{attr}' in {path}")
                
                # Check fields (datasets)
                for field in requirements.get('required_fields', []):
                    if field not in obj:
                        validation_results["errors"].append(f"Missing required field '{field}' in {path}")
                
                # Check groups
                for group in requirements.get('required_groups', []):
                    group_path = f"{path}/{group}"
                    if group_path.replace('entry/', '') not in obj:
                        validation_results["errors"].append(f"Missing required group '{group}' in {path}")
            
            # Check definition
            if 'entry' in f and 'definition' in f['entry'].attrs:
                definition = f['entry'].attrs['definition']
                if isinstance(definition, bytes):
                    definition = definition.decode()
                if definition != 'NXcanSAS':
                    validation_results["errors"].append(f"Incorrect definition: {definition}, expected 'NXcanSAS'")
            
            # Check canSAS_class
            if 'entry' in f and 'canSAS_class' in f['entry'].attrs:
                canSAS_class = f['entry'].attrs['canSAS_class']
                if isinstance(canSAS_class, bytes):
                    canSAS_class = canSAS_class.decode()
                if canSAS_class != 'SASentry':
                    validation_results["errors"].append(f"Incorrect canSAS_class: {canSAS_class}, expected 'SASentry'")
            
            # Extract structure for reporting
            def extract_structure(name, obj):
                path_parts = name.split('/')
                current = validation_results["structure"]
                for part in path_parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                if isinstance(obj, h5py.Group):
                    current[path_parts[-1]] = {
                        'type': 'group',
                        'attrs': dict(obj.attrs)
                    }
                else:
                    current[path_parts[-1]] = {
                        'type': 'dataset',
                        'shape': obj.shape,
                        'dtype': str(obj.dtype)
                    }
            
            f.visititems(extract_structure)
            
            validation_results["valid"] = len(validation_results["errors"]) == 0
            
    except Exception as e:
        validation_results["errors"].append(f"Error reading file: {e}")
    
    return validation_results

def print_saxs_structure(nexus_file_path):
    """
    Print the structure of a SAXS NeXus file.
    
    Args:
        nexus_file_path (str): Path to the NeXus file
    """
    try:
        with h5py.File(nexus_file_path, 'r') as f:
            print(f"\nStructure of {nexus_file_path}:")
            
            def print_structure(name, obj):
                indent = "  " * name.count('/')
                if isinstance(obj, h5py.Group):
                    # Handle both string and bytes attributes
                    nx_class_attr = obj.attrs.get('NX_class', '')
                    if isinstance(nx_class_attr, bytes):
                        nx_class = nx_class_attr.decode()
                    else:
                        nx_class = str(nx_class_attr) if nx_class_attr else ''
                    
                    canSAS_class_attr = obj.attrs.get('canSAS_class', '')
                    if isinstance(canSAS_class_attr, bytes):
                        canSAS_class = canSAS_class_attr.decode()
                    else:
                        canSAS_class = str(canSAS_class_attr) if canSAS_class_attr else ''
                    
                    definition_attr = obj.attrs.get('definition', '')
                    if isinstance(definition_attr, bytes):
                        definition = definition_attr.decode()
                    else:
                        definition = str(definition_attr) if definition_attr else ''
                    
                    class_info = f" [{nx_class}]" if nx_class else ""
                    class_info += f" [canSAS: {canSAS_class}]" if canSAS_class else ""
                    class_info += f" [def: {definition}]" if definition else ""
                    print(f"{indent}{name.split('/')[-1]}/{class_info}")
                else:
                    shape_info = f" {obj.shape}" if hasattr(obj, 'shape') else ""
                    dtype_info = f" ({obj.dtype})" if hasattr(obj, 'dtype') else ""
                    print(f"{indent}{name.split('/')[-1]}{shape_info}{dtype_info}")
            
            f.visititems(print_structure)
            
    except Exception as e:
        print(f"Error reading file structure: {e}")

# Add this at the end of the file for command-line usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 4 and sys.argv[1] == "--saxs-only":
        # SAXS-only mode
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        
        print("Creating SAXS-only NeXus file...")
        results = create_saxs_only_nexus(input_file, output_file, validate=True)
        
        if results["success"]:
            print(f"\n✓ Successfully created SAXS NeXus file: {results['output_file']}")
            print(f"  - Q points: {results['q_points']}")
            print(f"  - Q range: {results['q_range']}")
            print(f"  - Intensity range: {results['intensity_range']}")
            
            # Print structure
            print_saxs_structure(results['output_file'])
        else:
            print(f"\n✗ Failed to create SAXS NeXus file: {results.get('error', 'Unknown error')}")
            sys.exit(1)
    
    elif len(sys.argv) == 4:
        # Run the original combined SAXS + UV-vis processing
        print("Running combined SAXS + UV-vis processing...")
        input_saxs_file = sys.argv[1]
        input_uvvis_file = sys.argv[2]
        output_file = sys.argv[3]
        saxs_entry = parse_create_saxs_entry(input_saxs_file)
        uvvis_metadata, wavelengths, absorbances = parse_uvvis_file(input_uvvis_file)
        if uvvis_metadata and wavelengths.size > 0 and absorbances.size > 0:
            uvvis_entry = create_uvvis_entry(uvvis_metadata, wavelengths, absorbances)
        else:
            uvvis_entry = None
        create_saxs_uvvis_nexus(saxs_entry, uvvis_entry)
        print("Combined SAXS + UV-vis NeXus file created successfully.")
    
    else:
        print("Usage:")
        print("  python parse.py <input saxs file> <input uvvis file> <output file>     # Create combined SAXS + UV-vis file")
        print("  python parse.py --saxs-only <input saxs file> <output file>            # Create SAXS-only file")
        print()
        print("Examples:")
        print("  python parse.py input_saxs.nxs input_uvvis.txt output_combined.nxs")
        print("  python parse.py --saxs-only input.nxs saxs_only.nxs")
        sys.exit(1)
