/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

/**
 * @file Lambda roles for test infrastructure.
 *
 * This construct creates IAM roles needed for the test Lambda function including:
 * - VPC execution permissions
 * - CloudWatch Logs permissions
 */

import { region_info } from "aws-cdk-lib";
import {
  CompositePrincipal,
  Effect,
  IRole,
  ManagedPolicy,
  PolicyStatement,
  Role,
  ServicePrincipal
} from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

import { OSMLAccount } from "../types";

/**
 * Properties for LambdaRole construct.
 */
export interface LambdaRoleProps {
  /** The OSML account configuration. */
  readonly account: OSMLAccount;
  /** The name for the Lambda role. */
  readonly roleName: string;
  /** Optional existing Lambda role to use instead of creating a new one. */
  readonly existingLambdaRole?: IRole;
}

/**
 * Construct for creating IAM roles for test Lambda functions.
 * Follows tile-server pattern with ManagedPolicy and partition detection.
 */
export class LambdaRole extends Construct {
  /** The Lambda execution role. */
  public readonly lambdaRole: IRole;

  /** The AWS partition in which the roles will operate. */
  public readonly partition: string;

  /**
   * Creates a new LambdaRole construct.
   *
   * @param scope - The scope in which to define this construct
   * @param id - The construct ID
   * @param props - The construct properties
   */
  constructor(scope: Construct, id: string, props: LambdaRoleProps) {
    super(scope, id);

    this.partition = region_info.Fact.find(
      props.account.region,
      region_info.FactName.PARTITION
    )!;

    // Create or use existing lambda role
    this.lambdaRole = props.existingLambdaRole || this.createLambdaRole(props);
  }

  /**
   * Creates the lambda role with ManagedPolicy.
   *
   * @param props - The lambda role properties
   * @returns The created lambda role
   */
  private createLambdaRole(props: LambdaRoleProps): IRole {
    const lambdaRole = new Role(this, "GeoAgentLambdaRole", {
      roleName: props.roleName,
      assumedBy: new CompositePrincipal(
        new ServicePrincipal("lambda.amazonaws.com")
      ),
      description:
        "Allows the OversightML GeoAgent Integration Test lambda to access necessary AWS services (VPC, CloudWatch)"
    });

    const policy = new ManagedPolicy(this, "GeoAgentLambdaPolicy", {
      managedPolicyName: "GeoAgentLambdaPolicy"
    });

    // Add permissions for Lambda function configuration access
    const lambdaPolicyStatement = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: ["lambda:GetFunctionConfiguration"],
      resources: [
        `arn:${this.partition}:lambda:${props.account.region}:${props.account.id}:function:*`
      ]
    });

    // Add permissions for Lambda to access VPC resources and load balancers
    const ec2NetworkPolicyStatement = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        "elasticloadbalancing:DescribeLoadBalancers",
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "ec2:AssignPrivateIpAddresses",
        "ec2:UnassignPrivateIpAddresses",
        "ec2:DescribeInstances",
        "ec2:AttachNetworkInterface"
      ],
      resources: ["*"]
    });

    // Add permissions for CloudWatch Logs
    const cwPolicyStatement = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      resources: [
        `arn:${this.partition}:logs:${props.account.region}:${props.account.id}:*`
      ]
    });

    // Add permissions for S3 workspace bucket access (for test dataset uploads)
    const s3PolicyStatement = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      resources: [
        `arn:${this.partition}:s3:::*`,
        `arn:${this.partition}:s3:::*/*`
      ]
    });

    policy.addStatements(
      lambdaPolicyStatement,
      ec2NetworkPolicyStatement,
      cwPolicyStatement,
      s3PolicyStatement
    );

    lambdaRole.addManagedPolicy(policy);

    return lambdaRole;
  }
}
