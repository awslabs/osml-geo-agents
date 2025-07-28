# OversightML Geo Agents
![Build Badge](https://github.com/awslabs/osml-geo-agents/actions/workflows/build.yml/badge.svg)
![Python Badge](https://img.shields.io/badge/python-3.12-blue)
![GitHub License](https://img.shields.io/github/license/awslabs/osml-geo-agents?color=blue)

OversightML Geo Agents is a containerized application that provides geospatial and image processing tools for use by artificial intelligence agents.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Deployment](#deployment)
- [Development](#development)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

OversightML Geo Agents provides a set of geospatial tools that can be used by AI agents to process and analyze geospatial data. The tools are exposed through a Model Context Protocol (MCP) server, which allows AI agents to interact with the tools through a standardized interface.

## Features

The package provides the following geospatial operations:

- **Buffer Geometry**: Create a new geometry by expanding an input geometry by a specified distance
- **Cluster Features**: Group features based on spatial proximity
- **Correlate Datasets**: Match features from one dataset with features from another dataset
- **Filter Dataset**: Select features from a dataset based on spatial or attribute criteria
- **Sample Features**: Extract a small number of features from a dataset for inspection
- **Summarize Dataset**: Generate a natural language description of a dataset's columns
- **Translate Geometry**: Move a geometry by a specified distance and heading
- **Append Datasets**: Combine multiple datasets into a single dataset

## Project Structure

The project is organized as follows:

- `./src`: Main Python source code for the tools
- `./test`: Unit tests for the code in the src directory
- `./conda`: Configuration files for the conda environment
- `./docker`: Build files for containerizing the application
- `./cdk`: CDK project for deploying the application to AWS as a Bedrock Tool
- `./doc`: Documentation configuration files and auto-generated documentation

## Prerequisites

- Docker or Finch for container management
- Python 3.12+ (for local development)
- AWS credentials (if using AWS services)

## Installation

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/awslabs/osml-geo-agents.git
   cd osml-geo-agents
   ```

2. Create and activate the conda environment:
   ```bash
   conda env create -f conda/agent-environment.yml
   conda activate osml_geo_agents
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Deployment

There are two main ways to deploy and run the OversightML Geo Agents:

### Running as an MCP Server

#### Environment Setup

Create a `.env` file in the project root with the following variables:

```
WORKSPACE_LOCAL_CACHE=/path/to/your/workspace
AWS_DEFAULT_REGION=your-aws-region
```

Replace `/path/to/your/workspace` with a local directory path where you want to store workspace data, and `your-aws-region` with your preferred AWS region (e.g., `us-west-2`).

#### Using Docker or Finch Compose

You can use either [Docker](https://www.docker.com/) or [Finch](https://runfinch.com/) (an open source container runtime alternative) to run the MCP server. The commands are identical except for the executable name:

1. Build and start the container:
   ```bash
   # Using Docker
   docker compose up --build

   # Using Finch
   finch compose up --build
   ```

2. To run in detached mode:
   ```bash
   # Using Docker
   docker compose up -d --build

   # Using Finch
   finch compose up -d --build
   ```

3. To stop the container:
   ```bash
   # Using Docker
   docker compose down

   # Using Finch
   finch compose down
   ```

The MCP server will be available at `http://localhost:8000` and currently runs using Server-Sent Events (SSE) over HTTP. We plan to support STDIO and HTTP Streaming in the future, but there are currently compatibility issues with Cline and Finch that prevent us from doing so.

#### Configuring Cline to Use the MCP Server

To use the OversightML Geo Agents with Cline, you need to configure Cline to connect to the MCP server. Create or update your `cline_mcp_settings.json` file (typically located in your user settings directory) with the following configuration:

```json
{
  "mcpServers": {
    "osml-mcp": {
      "autoApprove": [
        "summarize_dataset",
        "sample_features"
      ],
      "timeout": 60,
      "url": "http://127.0.0.1:8000/sse",
      "transportType": "sse"
    }
  }
}
```

This configuration:
- Sets up the `osml-mcp` server connection
- Automatically approves the use of the `summarize_dataset` and `sample_features` tools
- Sets a timeout of 60 seconds for server responses
- Connects to the server at `http://127.0.0.1:8000/sse` using Server-Sent Events (SSE)

You can add more tools to the `autoApprove` array as needed, based on your security preferences.

### AWS Bedrock Integration

The project includes a CDK application that can be used to deploy the containerized application to AWS as a Bedrock Tool. This allows the geospatial tools to be used directly by AWS Bedrock agents.

For detailed instructions on deploying to AWS Bedrock, see the [CDK README](cdk/README.md).

## Development

The project uses tox for builds. To build the project:

```bash
tox
```

For more details on development practices and guidelines, see the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## Testing

Run tests using tox:

```bash
# Run all tests
tox

# Run specific tests
tox -e py312 -- test/aws/osml/test_foo.py
```

## Documentation

Generate documentation using Sphinx:

```bash
tox -e docs
```

The documentation will be available in `doc/_apidoc`.


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

### Security Issues

If you discover a potential security issue, please notify AWS/Amazon Security via the [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public GitHub issue.

## License

This project is licensed under the Apache-2.0 License. See the [LICENSE](LICENSE) file for details.
