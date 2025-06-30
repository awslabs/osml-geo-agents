/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import * as path from "path";

import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { FoundationModelIdentifier } from "aws-cdk-lib/aws-bedrock";
import { SubnetType, Vpc } from "aws-cdk-lib/aws-ec2";
import { Bucket } from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";
import { NagSuppressions } from "cdk-nag";

import { OSMLAgentToolLambda } from "./constructs/osml-agent-tool-lambda";
import { BedrockAgentLambda } from "./constructs/bedrock-agent-lambda";

/**
 * Properties for configuring the OSML Geo Agent Stack.
 * This interface defines the configuration options needed to deploy
 * the complete OSML Geo Agent infrastructure including VPC and workspace resources.
 */
interface OSMLGeoAgentStackProps extends StackProps {
  /**
   * The ID of the target VPC where the agent resources will be deployed.
   * The VPC must have private subnets with egress access for the agents to function properly.
   * @pattern ^vpc-[a-f0-9]{8,17}$
   */
  targetVpcId: string;

  /**
   * The name of the S3 bucket used as a shared workspace for the agent and compute cluster.
   * This bucket stores geospatial assets and intermediate processing results.
   * @pattern ^[a-z0-9][a-z0-9.-]*[a-z0-9]$
   * @minLength 3
   * @maxLength 63
   */
  workspaceBucketName: string;
}

/**
 * Validates the configuration properties for the OSML Geo Agent Stack.
 *
 * This function performs input validation to ensure that the provided configuration
 * meets AWS requirements and follows proper naming conventions before deploying
 * the infrastructure. It validates both the VPC ID format and S3 bucket name
 * to prevent deployment failures and ensure proper resource identification.
 *
 * @param {OSMLGeoAgentStackProps} props - The configuration properties to validate
 * @throws {Error} When validation fails with a descriptive error message
 */
export const validateProps = (props: OSMLGeoAgentStackProps) => {
  // Validate VPC ID format: must start with 'vpc-' followed by 8-17 hexadecimal characters
  // This matches AWS VPC ID format requirements (e.g., vpc-12345678, vpc-abcdef1234567890)
  if (!/^vpc-[a-f0-9]{8,17}$/.test(props.targetVpcId)) {
    throw new Error(`Invalid VPC ID format: ${props.targetVpcId}`);
  }

  // Validate S3 bucket name length: must be 3-63 characters long
  if (
    props.workspaceBucketName.length < 3 ||
    props.workspaceBucketName.length > 63
  ) {
    throw new Error(
      `Invalid S3 bucket name length: ${props.workspaceBucketName}`
    );
  }

  // Validate S3 bucket name format: must start and end with alphanumeric characters
  // and can contain lowercase letters, numbers, hyphens, and dots
  // This follows AWS S3 bucket naming conventions
  if (!/^[a-z0-9][a-z0-9.-]*[a-z0-9]$/.test(props.workspaceBucketName)) {
    throw new Error(
      `Invalid S3 bucket name format: ${props.workspaceBucketName}`
    );
  }

  // Additional S3 bucket name validation rules
  if (props.workspaceBucketName.includes("..")) {
    throw new Error(`Invalid S3 bucket name: ${props.workspaceBucketName}`);
  }

  if (
    props.workspaceBucketName.includes(".-") ||
    props.workspaceBucketName.includes("-.")
  ) {
    throw new Error(`Invalid S3 bucket name: ${props.workspaceBucketName}`);
  }
};

/**
 * CDK Stack that deploys the complete OSML Geo Agent infrastructure.
 *
 * This stack creates a comprehensive geospatial AI system using AWS Bedrock agents
 * with specialized Lambda functions for geospatial operations. The system includes:
 *
 * - A containerized Lambda function for geospatial tool operations
 * - A Bedrock agent configured with geospatial action groups
 * - Integration with existing VPC and S3 workspace resources
 *
 * The agents run within a VPC and require access to a workspace bucket for storing
 * large geospatial datasets and processing results.
 */
export class OSMLGeoAgentStack extends Stack {
  /**
   * Creates a new instance of the OSML Geo Agent Stack.
   *
   * This constructor sets up the complete infrastructure for the OSML Geo Agent system,
   * including the geospatial tools Lambda function and the Bedrock agent with proper
   * networking, permissions, and configuration.
   *
   * @param { Construct } scope - The construct scope in which to create the stack
   * @param { string } id - The unique identifier for this stack
   * @param { OSMLGeoAgentStackProps } props - Configuration properties including VPC ID and workspace bucket name
   */
  constructor(scope: Construct, id: string, props: OSMLGeoAgentStackProps) {
    super(scope, id, props);

    // Validate the configuration properties before proceeding
    validateProps(props);

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
      configPath: path.join(__dirname, "..", "osml-geo-agents-config"),
      alias: "dev"
    });

    // Add CDK-NAG suppression for the Lambda function's default policy
    NagSuppressions.addResourceSuppressions(
      this,
      [
        {
          id: "AwsSolutions-IAM5",
          reason:
            "Lambda function default policy contains necessary permissions for VPC and CloudWatch integration",
          appliesTo: ["Resource::*"]
        }
      ],
      true
    );
  }
}
