/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { join } from "node:path";

import { Duration, Stack, StackProps } from "aws-cdk-lib";
import { FoundationModelIdentifier } from "aws-cdk-lib/aws-bedrock";
import { SubnetType, Vpc } from "aws-cdk-lib/aws-ec2";
import { Bucket } from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

import { BedrockAgentLambda } from "./bedrock-agent-lambda";
import { OSMLAgentToolLambda } from "./osml-geo-agent-tool-lambda";

interface OSMLGeoAgentStackProps extends StackProps {
  targetVpcId: string;
  workspaceBucketName: string;
}

export class OSMLGeoAgentStack extends Stack {
  constructor(scope: Construct, id: string, props: OSMLGeoAgentStackProps) {
    super(scope, id, props);

    // The agents run within a VPC and need access to a workspace but it is assumed those
    // resources have already been created either manually or by a different CDK project.
    const vpc = Vpc.fromLookup(this, "TargetVpc", {
      vpcId: props.targetVpcId
    });
    const workspaceBucket = Bucket.fromBucketName(
      this,
      "GeoWorkspaceBucket",
      props.workspaceBucketName
    );

    const geoToolsLambda = new OSMLAgentToolLambda(this, "GeoToolsLambda", {
      vpc: vpc,
      workspaceBucket: workspaceBucket,
      vpcSubnets: {
        subnetType: SubnetType.PRIVATE_WITH_EGRESS
      },
      memorySize: 2048,
      timeout: Duration.minutes(15)
    });

    // Create the Bedrock Agent
    new BedrockAgentLambda(this, "GeoAgent", {
      handlerFunction: geoToolsLambda.function,
      foundationModel:
        FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_5_SONNET_20241022_V2_0,
      idleSessionTtlInSeconds: 3600, // 1 hour
      configPath: join(__dirname, "..", "osml-geo-agents-config"),
      alias: "dev"
    });
  }
}
