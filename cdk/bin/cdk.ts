#!/usr/bin/env node

/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import * as cdk from 'aws-cdk-lib';
import { OSMLGeoAgentStack } from '../lib/osml-geo-agent-stack';

const app = new cdk.App();

// This stack will be created to work with the default account/region.
// For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
const environment = {
  account: process.env.CDK_DEPLOY_ACCOUNT || process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEPLOY_REGION || process.env.CDK_DEFAULT_REGION
};

console.log(`Using Environment: ${JSON.stringify(environment, null, 2)}`);

const stack = new OSMLGeoAgentStack(app, 'OSML-GeoAgent', {
  env: environment,
  targetVpcId: app.node.tryGetContext('targetVpcId'),
  workspaceBucketName: app.node.tryGetContext('workspaceBucketName'),
  description:
      "OSML GeoAgent, Guidance for Processing Overhead Imagery on AWS (SO9240)"
});
