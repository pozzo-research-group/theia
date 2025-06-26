from nomad.config.models.plugins import ExampleUploadEntryPoint

example_upload_entry_point = ExampleUploadEntryPoint(
    title = 'My Example Upload',
    category = 'Examples',
    description = 'Description of this example upload.',
    resources=['example_uploads/getting_started/*']
)