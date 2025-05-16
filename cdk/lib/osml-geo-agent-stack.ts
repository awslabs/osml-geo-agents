/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { OSMLAgentToolLambda } from './osml-geo-agent-tool-lambda';
import { BedrockAgentLambda } from "./bedrock-agent-lambda";
import * as path from 'path';
import * as bedrock from "aws-cdk-lib/aws-bedrock";

interface OSMLGeoAgentStackProps extends cdk.StackProps {
  targetVpcId: string;
  workspaceBucketName: string;
}

export class OSMLGeoAgentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: OSMLGeoAgentStackProps) {
    super(scope, id, props);

    // The agents run within a VPC and need access to a workspace but it is assumed those
    // resources have already been created either manually or by a different CDK project.
    const vpc = ec2.Vpc.fromLookup(this, 'TargetVpc', {
      vpcId: props.targetVpcId
    });
    const workspaceBucket = s3.Bucket.fromBucketName(this, 'GeoWorkspaceBucket',
        props.workspaceBucketName);

    const geoToolsLambda = new OSMLAgentToolLambda(this, 'GeoToolsLambda', {
      vpc: vpc,
      workspaceBucket: workspaceBucket,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      memorySize: 2048,
      timeout: cdk.Duration.minutes(15),
    });

    // Create the Bedrock Agent
    const oversightAgent = new BedrockAgentLambda(this, 'GeoAgent', {
      handlerFunction: geoToolsLambda.function,
      foundationModel: bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_5_SONNET_20241022_V2_0,
      idleSessionTtlInSeconds: 3600, // 1 hour
      configPath: path.join(__dirname, '..', 'osml-geo-agents-config'),
      alias: 'dev'
    });
  }

}
