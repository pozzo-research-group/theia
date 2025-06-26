import logging

from nomad.datamodel import EntryArchive

from nomad_theia_plugin.parsers.parser import NewParser

p = NewParser()
a = EntryArchive()
p.parse('../data/SAXS_UV_VIS_processing_example.hdf5', a, logger=logging.getLogger())

print(a.m_to_dict())