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
import { OSMLGeoAgentStack } from "../lib/osml-geo-agent-stack";
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
 * - VPC and S3 workspace configuration
 */
const { projectName, account, config } = loadDeploymentConfig();

// -----------------------------------------------------------------------------
// Define and Deploy the OSMLGeoAgentStack
// -----------------------------------------------------------------------------

new OSMLGeoAgentStack(app, projectName, {
  env: {
    account: account.id,
    region: account.region
  },
  targetVpcId: config.targetVpcId,
  workspaceBucketName: config.workspaceBucketName,
  // Solution ID 'SO9240' should be verified to match the official AWS Solutions reference.
  description:
    "OSML GeoAgent, Guidance for Processing Overhead Imagery on AWS (SO9240)"
});
