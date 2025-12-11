# Product Overview

**OversightML Geo Agents** provides geospatial and image processing tools for AI agents.

## Purpose

Enables AI agents to perform geospatial operations through:
- **MCP Server**: Model Context Protocol interface at `http://localhost:8000`
- **AWS Bedrock**: Lambda-backed agent tools via CDK deployment

## Core Capabilities

| Tool | Description |
|------|-------------|
| Buffer Geometry | Expand geometries by specified distance |
| Cluster Features | Group features by spatial proximity |
| Correlate Datasets | Match features across datasets |
| Filter Dataset | Select features by spatial/attribute criteria |
| Sample Features | Extract feature subsets for inspection |
| Summarize Dataset | Generate natural language dataset descriptions |
| Translate Geometry | Move geometries by distance and heading |
| Append Datasets | Combine multiple datasets |
| Workspace Management | Load, list, and unload geospatial data |

## Key Libraries

- **Geospatial**: geopandas, shapely, pyproj, gdal
- **MCP Server**: mcp, starlette, uvicorn, sse-starlette
- **AWS**: boto3, awslambdaric

## Quick Start

```bash
# Local development
conda env create -f conda/agent-environment.yml
conda activate osml_geo_agents
pip install -e .

# Run MCP server
docker compose up --build
```
