# OSML Geo Agents – CDK Infrastructure

This CDK project deploys the core infrastructure for running **OSML Geo Agents** on AWS. It includes an ECS Fargate service running the MCP server behind an Application Load Balancer (ALB) within a private VPC, and an **Amazon Bedrock Agent** for orchestration.

## Security Model

The OSML Geo Agents infrastructure uses **network isolation** as its primary security mechanism:

- **Private VPC Deployment**: The MCP server runs in ECS Fargate within private subnets with no direct internet access
- **ALB as Entry Point**: The Application Load Balancer is the only entry point, accessible only from within the VPC
- **No Public Endpoints**: No API Gateway or public-facing endpoints - all access is VPC-internal
- **Security Groups**: Fine-grained network access control through VPC security groups
- **IAM Roles**: ECS tasks use IAM roles with least-privilege permissions for AWS service access

## Architecture Overview

```ascii

Private VPC Access:
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   VPC Client    │────▶│       ALB        │────▶│  ECS Fargate     │
│                 │     │  (Port 80)       │     │  MCP Server      │
└─────────────────┘     └──────────────────┘     └──────────────────┘
                                                           │
                                                           ▼
                                                  ┌──────────────────┐
                                                  │   S3 Workspace   │
                                                  └──────────────────┘
```

---

## Key Features

- **Private VPC Deployment**: The MCP server runs in ECS Fargate within a private VPC, accessible only through the Application Load Balancer
- **S3 Workspace Integration**: Persistent storage for geospatial data processing
- **Integration Testing**: Built-in test infrastructure to validate deployed services that run within the VPC

---

## Prerequisites

Before deploying, ensure the following tools and resources are available:

- **AWS CLI** configured with credentials
- **AWS CDK CLI** installed (`npm install -g aws-cdk`)
- **Node.js** and **npm** installed
- **Docker** installed and running (for building container images)
- An existing **VPC** with private subnets and NAT Gateway
- An **S3 bucket** for MCP server workspace storage

---

## Configuration

### Deployment File: `bin/deployment/deployment.json`

This file defines your deployment environment. Copy the example file and customize it:

```bash
cp bin/deployment/deployment.json.example bin/deployment/deployment.json
```

Update the contents with your environment-specific values:

```json
{
  "projectName": "<YOUR-PROJECT-NAME>",
  "account": {
    "id": "<YOUR-ACCOUNT-ID>",
    "region": "<YOUR-REGION>",
    "prodLike": false,
    "isAdc": false
  },
  "networkConfig": {
    "VPC_ID": "<YOUR-VPC-ID>",
    "TARGET_SUBNETS": ["<SUBNET-1>", "<SUBNET-2>"],
    "SECURITY_GROUP_ID": "<YOUR-SECURITY-GROUP-ID>"
  },
  "geoAgentConfig": {
    "WORKSPACE_BUCKET_NAME": "<YOUR-WORKSPACE-BUCKET-NAME>",
    "SERVICE_NAME_ABBREVIATION": "GA",
    "MCP_SERVER_PORT": 8080,
    "MCP_SERVER_CPU": 2048,
    "MCP_SERVER_MEMORY_SIZE": 4096
  },
  "deployIntegrationTests": true
}
```

**Note:** This file is validated at runtime to ensure all required fields are provided. Deployment will fail if any required fields are missing or invalid.

---

## Deployment Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Synthesize the Stack

```bash
cdk synth
```

### 3. Deploy the Stack

```bash
cdk deploy
```

This command will:

- Validate `deployment.json`
- Synthesize the CloudFormation template
- Deploy the infrastructure to your AWS account

---

## Project Structure

```
.
├── bin/
│   ├── app.ts                        # Entry point, loads config and launches stack
│   └── deployment/
│       ├── deployment.json           # Your environment-specific config
│       ├── deployment.json.example   # Template for creating new configs
│       └── load-deployment.ts        # Configuration loader and validator
├── lib/
│   ├── network-stack.ts              # VPC and security group configuration
│   ├── osml-geo-agent-stack.ts       # Main stack: ECS Fargate, ALB, S3 workspace
│   ├── test-stack.ts                 # Integration test infrastructure
│   ├── stack-props.ts                # Stack property interfaces and validation
│   ├── nag-suppressions.ts           # CDK Nag compliance suppressions
│   └── constructs/
│       ├── bedrock-agent-lambda.ts   # Bedrock agent construct
│       └── osml-agent-tool-lambda.ts # Lambda container definition
├── test/                             # Unit tests and cdk-nag checks
├── osml-geo-agents-config/           # Bedrock agent configuration
└── package.json                      # Project config and npm scripts
```

---

## Development & Testing

### Useful Commands

| Command         | Description                                          |
| --------------- | ---------------------------------------------------- |
| `npm run build` | Compile TypeScript to JavaScript                     |
| `npm run watch` | Auto-recompile on file changes                       |
| `npm run test`  | Run Jest unit tests                                  |
| `cdk synth`     | Generate CloudFormation template                     |
| `cdk diff`      | Compare local stack with deployed version            |
| `cdk deploy`    | Deploy the CDK stack                                 |
| `cdk destroy`   | Remove the deployed stack                            |
| `cdk bootstrap` | Bootstrap CDK in your AWS account (first-time setup) |
| `cdk list`      | List all stacks in the app                           |

---

## Security & Best Practices

This project integrates **cdk-nag** to validate infrastructure against AWS security best practices. Running `npm run test` will:

- Detect overly permissive IAM roles and security groups
- Ensure encryption is enabled where applicable
- Warn about missing logging or compliance settings

**Review the cdk-nag report** to maintain compliance and security posture before production deployments.

For deeper hardening guidance, refer to:

- [AWS CDK Security and Safety Dev Guide](https://docs.aws.amazon.com/cdk/v2/guide/security.html)
- Use of [`CliCredentialsStackSynthesizer`](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.CliCredentialsStackSynthesizer.html) for controlling credential use

---

## Summary

This CDK project provides infrastructure-as-code for deploying geospatial AI capabilities using AWS Bedrock and Lambda. It includes security validations via cdk-nag and supports deployment across multiple environments through configuration files.

For questions or contributions, please open an issue or PR.
