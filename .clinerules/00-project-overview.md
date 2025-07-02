`OversightML Geo Agents` is a project that provides geospatial and image processing tools
for use by artificial intelligence agents. The project is organized as follows:

`./src`: This directory contains the main Python source code for the tools.
`./test`: This directory contains the unit tests for the code in the src directory.
`./conda`: This directory contains configuration files that specify the conda environment needed to run the tools application.
`./docker`: This directory contains build files that show how the code is combined with the conda environment into an application.
`./cdk`: This directory is a CDK project that can be used to deploy the containerized application to AWS as a Bedrock Tool
`./doc`: This directory contains documentation configuration files and documentation automatically generated from the comments in ./src

The project uses tox for builds and follows Python best practices by defining the build system in
pyproject.toml, setup.cfg, and setup.py
