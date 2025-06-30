/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { join } from "node:path";

import { Duration, Size } from "aws-cdk-lib";
import {
  ISecurityGroup,
  IVpc,
  SubnetSelection,
  SubnetType
} from "aws-cdk-lib/aws-ec2";
import { DockerImageAsset, Platform } from "aws-cdk-lib/aws-ecr-assets";
import {
  PolicyStatement,
  Role,
  ServicePrincipal,
  PolicyDocument,
  Effect
} from "aws-cdk-lib/aws-iam";
import {
  Architecture,
  DockerImageCode,
  DockerImageFunction,
  IFunction,
  Tracing
} from "aws-cdk-lib/aws-lambda";
import { IBucket } from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";
import { NagSuppressions } from "cdk-nag";

/**
 * Properties for configuring an OSML Agent Tool Lambda function.
 * This interface defines the configuration options needed to create and deploy
 * a Lambda function that serves as a tool for the OSML Agent system.
 */
export interface OSMLAgentToolLambdaProps {
  /**
   * VPC to deploy the Lambda function into
   */
  vpc: IVpc;

  /**
   * The S3 bucket used as a shared workspace for the agent and compute cluster
   */
  workspaceBucket: IBucket;

  /**
   * VPC subnets to deploy the Lambda function into
   * @default - private subnets
   */
  vpcSubnets?: SubnetSelection;

  /**
   * Memory limit for the Lambda function in MB
   * @default 1024
   */
  memorySize?: number;

  /**
   * Ephemeral storage size limit for the Lambda function in MB
   * @default Size.gibibytes(10)
   */
  storageSize?: Size;

  /**
   * Timeout for the Lambda function in seconds
   * @default 300 (5 minutes)
   */
  timeout?: Duration;

  /**
   * IAM role statements to add to the Lambda execution role
   */
  policyStatements?: PolicyStatement[];

  /**
   * Security groups to attach to the Lambda function
   * @default - a new security group is created
   */
  securityGroups?: ISecurityGroup[];
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
  public readonly function: IFunction;

  /**
   * Creates a new instance of OSMLAgentToolLambda.
   * @param { Construct } scope The construct scope in which to create the Lambda function
   * @param { string } id The unique identifier for this construct
   * @param { OSMLAgentToolLambdaProps } props Configuration properties for the Lambda function including VPC, memory, storage, and permissions
   */
  constructor(scope: Construct, id: string, props: OSMLAgentToolLambdaProps) {
    super(scope, id);

    // Create a custom IAM role with specific permissions instead of using managed policies
    const lambdaRole = new Role(this, "LambdaExecutionRole", {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      description: "Custom execution role for OSML Agent Tool Lambda function",
      inlinePolicies: {
        CloudWatchLogsPolicy: new PolicyDocument({
          statements: [
            new PolicyStatement({
              effect: Effect.ALLOW,
              actions: [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
              ],
              resources: [
                `arn:aws:logs:${scope.node.tryGetContext("region") || "*"}:${scope.node.tryGetContext("account") || "*"}:log-group:/aws/lambda/${id}-*`
              ]
            })
          ]
        }),
        VPCAccessPolicy: new PolicyDocument({
          statements: [
            new PolicyStatement({
              effect: Effect.ALLOW,
              actions: [
                "ec2:CreateNetworkInterface",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DeleteNetworkInterface",
                "ec2:AssignPrivateIpAddresses",
                "ec2:UnassignPrivateIpAddresses"
              ],
              resources: ["*"]
            })
          ]
        }),
        S3WorkspacePolicy: new PolicyDocument({
          statements: [
            new PolicyStatement({
              effect: Effect.ALLOW,
              actions: [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"
              ],
              resources: [
                props.workspaceBucket.bucketArn,
                `${props.workspaceBucket.bucketArn}/*`
              ]
            })
          ]
        })
      }
    });

    // Add CDK-NAG suppressions for necessary wildcard permissions
    NagSuppressions.addResourceSuppressions(
      lambdaRole,
      [
        {
          id: "AwsSolutions-IAM5",
          reason:
            "VPC Lambda functions require EC2 network interface permissions which cannot be scoped to specific resources",
          appliesTo: ["Resource::*"]
        },
        {
          id: "AwsSolutions-IAM5",
          reason:
            "CloudWatch Logs permissions are scoped to the specific Lambda function's log group pattern",
          appliesTo: [
            `Resource::arn:aws:logs:*:*:log-group:/aws/lambda/${id}-*`
          ]
        },
        {
          id: "AwsSolutions-IAM5",
          reason:
            "S3 bucket permissions are scoped to the specific workspace bucket and its contents",
          appliesTo: [
            `Resource::arn:<AWS::Partition>:s3:::${props.workspaceBucket.bucketName}/*`
          ]
        },
        {
          id: "AwsSolutions-IAM5",
          reason:
            "Lambda function default policy contains necessary permissions for VPC and CloudWatch integration",
          appliesTo: ["Resource::*"]
        }
      ],
      true
    );

    // Create a Docker image asset from the Dockerfile
    const dockerAsset = new DockerImageAsset(this, "ToolImage", {
      directory: join(__dirname, "../../.."),
      file: "docker/Dockerfile.agents",
      platform: Platform.LINUX_AMD64
    });

    // Create the Lambda function
    this.function = new DockerImageFunction(this, "Default", {
      code: DockerImageCode.fromEcr(dockerAsset.repository, {
        tagOrDigest: dockerAsset.imageTag
      }),
      role: lambdaRole,
      vpc: props.vpc,
      vpcSubnets: props.vpcSubnets ?? {
        subnetType: SubnetType.PRIVATE_WITH_EGRESS
      },
      securityGroups: props.securityGroups,
      memorySize: props?.memorySize ?? 1024,
      ephemeralStorageSize: props?.storageSize ?? Size.gibibytes(10),
      timeout: props?.timeout ?? Duration.seconds(300),
      environment: {
        WORKSPACE_BUCKET_NAME: props.workspaceBucket.bucketName
      },
      architecture: Architecture.X86_64,
      tracing: Tracing.ACTIVE,
      allowAllOutbound: true
    });

    // Add custom policy statements if provided
    if (props?.policyStatements) {
      props.policyStatements.forEach((statement) => {
        this.function.addToRolePolicy(statement);
      });
    }
  }
}
