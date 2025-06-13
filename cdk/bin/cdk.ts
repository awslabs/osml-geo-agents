#!/usr/bin/env node

/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { App, UnscopedValidationError} from "aws-cdk-lib";
import { OSMLGeoAgentStack } from '../lib/osml-geo-agent-stack';
import { appConfig } from "./app_config";

const app = new App();

// This stack is configured from cdk.context.json
const environment = {
  account: appConfig.account.id,
  region: appConfig.account.region
};

console.log(`Using environment from cdk.context.json: ${JSON.stringify(environment, null, 2)}`);

const targetVpcId = appConfig.geoAgent.config?.targetVpcId;
const workspaceBucketName = appConfig.geoAgent.config?.workspaceBucketName;
if (!targetVpcId) {
  throw new UnscopedValidationError("targetVpcId is required in geoAgent config");
}
if (!workspaceBucketName) {
  throw new UnscopedValidationError("workspaceBucketName is required in geoAgent config");
}
const stack = new OSMLGeoAgentStack(app, `${appConfig.projectName}-GeoAgent`, {
  env: environment,
  targetVpcId: String(targetVpcId),
  workspaceBucketName: String(workspaceBucketName),
  description:
      "OSML GeoAgent, Guidance for Processing Overhead Imagery on AWS (SO9240)"
});
