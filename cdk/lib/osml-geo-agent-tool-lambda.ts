/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import * as ecs from "aws-cdk-lib/aws-ecs";

/**
 * Properties for configuring an OSML Agent Tool Lambda function.
 * This interface defines the configuration options needed to create and deploy
 * a Lambda function that serves as a tool for the OSML Agent system.
 */
export interface OSMLAgentToolLambdaProps {
  /**
   * VPC to deploy the Lambda function into
   */
  vpc: ec2.IVpc;

  /**
   * The S3 bucket used as a shared workspace for the agent and compute cluster
   */
  workspaceBucket: s3.IBucket;

  /**
   * VPC subnets to deploy the Lambda function into
   * @default - private subnets
   */
  vpcSubnets?: ec2.SubnetSelection;

  /**
   * Memory limit for the Lambda function in MB
   * @default 1024
   */
  memorySize?: number;

  /**
   * Ephemeral storage size limit for the Lambda function in MB
   * @default Size.gibibytes(10)
   */
  storageSize?: cdk.Size;

  /**
   * Timeout for the Lambda function in seconds
   * @default 300 (5 minutes)
   */
  timeout?: cdk.Duration;

  /**
   * IAM role statements to add to the Lambda execution role
   */
  policyStatements?: iam.PolicyStatement[];

  /**
   * Security groups to attach to the Lambda function
   * @default - a new security group is created
   */
  securityGroups?: ec2.ISecurityGroup[];
}

/**
 * Construct that creates a Lambda function for OSML Agent Tool operations.
 * This class sets up a containerized Lambda function with the necessary configurations,
 * permissions, and resources to execute OSML Agent tools within a VPC environment.
 */
export class OSMLAgentToolLambda extends Construct {
  /**
   * The underlying Lambda function
   */
  public readonly function: lambda.IFunction;

  /**
   * Creates a new instance of OSMLAgentToolLambda.
   * @param { Construct } scope The construct scope in which to create the Lambda function
   * @param { string } id The unique identifier for this construct
   * @param { OSMLAgentToolLambdaProps } props Configuration properties for the Lambda function including VPC, memory, storage, and permissions
   */
  constructor(scope: Construct, id: string, props: OSMLAgentToolLambdaProps) {
    super(scope, id);

    // Create a Docker image asset from the Dockerfile
    const dockerAsset = new ecr_assets.DockerImageAsset(this, 'ToolImage', {
      directory: path.join(__dirname, '../..'),
      file: 'docker/Dockerfile.agents',
      platform: ecr_assets.Platform.LINUX_AMD64,
    });

    // Create the Lambda function
    this.function = new lambda.DockerImageFunction(this, 'Default', {
      code: lambda.DockerImageCode.fromEcr(dockerAsset.repository, {
        tagOrDigest: dockerAsset.imageTag,
      }),
      vpc: props.vpc,
      vpcSubnets: props.vpcSubnets ?? { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: props.securityGroups,
      memorySize: props?.memorySize ?? 1024,
      ephemeralStorageSize: props?.storageSize ?? cdk.Size.gibibytes(10),
      timeout: props?.timeout ?? cdk.Duration.seconds(300),
      environment: {
        WORKSPACE_BUCKET_NAME: props.workspaceBucket.bucketName
      },
      architecture: lambda.Architecture.X86_64,
      tracing: lambda.Tracing.ACTIVE,
      allowAllOutbound: true,
    });

    // Add custom policy statements if provided
    if (props?.policyStatements) {
      props.policyStatements.forEach(statement => {
        this.function.addToRolePolicy(statement);
      });
    }

    // Add CloudWatch Logs permissions
    this.function.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));

    this.function.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:GetBucketLocation'
      ],
      resources: [
        props.workspaceBucket.bucketArn,
        `${props.workspaceBucket.bucketArn}/*`
      ]
    }));
    props.workspaceBucket.grantReadWrite(this.function);
  }
}
