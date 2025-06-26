from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

import os

import h5py
from nomad.config import config

#from nomad.datamodel.metainfo.workflow import Workflow
from nomad.parsing.parser import MatchingParser

from nomad_theia_plugin.schema_packages.schema_package import (
    NanoparticleExperiment,
    SAXSResults,
    UVVisNirResult,
)

configuration = config.get_plugin_entry_point(
    'nomad_theia_plugin.parsers:parser_entry_point'
)


class NewParser(MatchingParser):
    def parse(
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        child_archives: dict[str, 'EntryArchive'] = None,
    ) -> None:
        #logger.info('NewParser.parse', parameter=configuration.parameter)
        logger.info(f' Theia Parser called {mainfile}')
        #archive.workflow2 = Workflow(name='test')
        with h5py.File(mainfile, 'r') as f:
            # Parse UV-Vis data
            absorbance = f['entry2/data/intensity'][()]
            wavelength = f['entry2/data/wavelength'][()]

            uvvis = UVVisNirResult(
                absorbance=absorbance,
                wavelength=wavelength
            )

            # Parse SAXS data
            intensity = f['processed/result/data'][()].flatten()
            errors = f['processed/result/errors'][()].flatten()
            q = f['processed/result/q'][()]

            saxs = SAXSResults(
                intensities=intensity,
                errors=errors,
                q=q
            )

            # Assign to archive
            archive.data = NanoparticleExperiment(
                UVvis_data=uvvis,
                SAXS_data=saxs
            )
