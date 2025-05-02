from nomad.config.models.plugins import ExampleUploadEntryPoint
from pydantic import Field


class NewExampleUploadEntryPoint(ExampleUploadEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_theia_plugin.example_uploads import NewExample

        return NewExample(**self.dict())


example_entry_point = NewExampleUploadEntryPoint(
    name='NewExampleUpload',
    description='New example upload entry point configuration.',
    mainfile_name_re='.*\.newmainfilename',
)