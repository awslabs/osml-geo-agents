#!/usr/bin/env node

/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

/**
 * @file Entry point for the OSML GeoAgent CDK application.
 *
 * This file bootstraps the CDK app, loads deployment configuration,
 * and instantiates the OSMLGeoAgentStack with validated parameters.
 *
 */

import { App } from "aws-cdk-lib";
import { IVpc, Vpc } from "aws-cdk-lib/aws-ec2";

import { NetworkStack } from "../lib/network-stack";
import { OSMLGeoAgentStack } from "../lib/osml-geo-agent-stack";
import { TestStack } from "../lib/test-stack";
import { loadDeploymentConfig } from "./deployment/load-deployment";

// -----------------------------------------------------------------------------
// Initialize CDK Application
// -----------------------------------------------------------------------------

const app = new App();

/**
 * Load and validate deployment configuration from deployment.json.
 *
 * This includes:
 * - Project name
 * - AWS account ID and region
 * - Network configuration
 * - S3 workspace configuration
 */
const deployment = loadDeploymentConfig();

// -----------------------------------------------------------------------------
// Create VPC (only if importing existing VPC)
// -----------------------------------------------------------------------------

let vpc: IVpc | undefined;
if (deployment.networkConfig?.VPC_ID) {
  // Import existing VPC
  vpc = Vpc.fromLookup(app, "ImportedVPC", {
    vpcId: deployment.networkConfig.VPC_ID
  });
}

// -----------------------------------------------------------------------------
// Deploy the network stack
// -----------------------------------------------------------------------------

const networkStack = new NetworkStack(
  app,
  `${deployment.projectName}-GeoAgentNetwork`,
  {
    env: {
      account: deployment.account.id,
      region: deployment.account.region
    },
    deployment: deployment,
    vpc: vpc,
    mcpServerPort: deployment.geoAgentConfig?.MCP_SERVER_PORT
  }
);

// -----------------------------------------------------------------------------
// Define and Deploy the OSMLGeoAgentStack
// -----------------------------------------------------------------------------

const geoAgentStack = new OSMLGeoAgentStack(
  app,
  `${deployment.projectName}-GeoAgent`,
  {
    env: {
      account: deployment.account.id,
      region: deployment.account.region
    },
    projectName: deployment.projectName,
    prodLike: deployment.account.prodLike,
    isAdc: deployment.account.isAdc,
    serviceNameAbbreviation:
      deployment.geoAgentConfig?.SERVICE_NAME_ABBREVIATION,
    vpc: networkStack.network.vpc,
    securityGroup: networkStack.network.securityGroup,
    workspaceBucketName: deployment.geoAgentConfig?.WORKSPACE_BUCKET_NAME,
    mcpServerPort: deployment.geoAgentConfig?.MCP_SERVER_PORT,
    mcpServerCpu: deployment.geoAgentConfig?.MCP_SERVER_CPU,
    mcpServerMemorySize: deployment.geoAgentConfig?.MCP_SERVER_MEMORY_SIZE,
    description:
      "OSML GeoAgent, Guidance for Processing Overhead Imagery on AWS (SO9240)"
  }
);

geoAgentStack.node.addDependency(networkStack);

// -----------------------------------------------------------------------------
// Deploy the TestStack (if integration tests enabled)
// -----------------------------------------------------------------------------

if (deployment.deployIntegrationTests) {
  const testStack = new TestStack(
    app,
    `${deployment.projectName}-GeoAgentTest`,
    {
      env: {
        account: deployment.account.id,
        region: deployment.account.region
      },
      deployment: deployment,
      vpc: networkStack.network.vpc,
      albDnsName: geoAgentStack.alb.loadBalancerDnsName,
      securityGroup: networkStack.network.securityGroup,
      workspaceBucketName: geoAgentStack.workspaceBucket.bucketName
    }
  );
  testStack.node.addDependency(geoAgentStack);
}
