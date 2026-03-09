/*
 * Copyright 2025-2026 Amazon.com, Inc. or its affiliates.
 */

/**
 * @file TestStack for deploying test infrastructure.
 *
 * This stack deploys the Test construct which includes:
 * - Lambda function for running integration tests
 * - IAM roles with necessary permissions
 * - Test configuration
 */

import { Stack, StackProps } from "aws-cdk-lib";
import { ISecurityGroup, IVpc } from "aws-cdk-lib/aws-ec2";
import { IRole } from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

import { DeploymentConfig } from "../bin/deployment/load-deployment";
import { LambdaRole } from "./constructs/test/lambda-roles";
import { Test } from "./constructs/test/test";

/**
 * Properties for the TestStack.
 */
export interface TestStackProps extends StackProps {
  /** The deployment configuration. */
  deployment: DeploymentConfig;
  /** The VPC to use for the test Lambda. */
  vpc: IVpc;
  /** Optional security group for test Lambda. */
  securityGroup?: ISecurityGroup;
  /** Optional existing Lambda role. */
  existingLambdaRole?: IRole;
}

/**
 * Stack for deploying test resources.
 */
export class TestStack extends Stack {
  /** The Lambda role for tests. */
  public readonly role: LambdaRole;

  /** The test construct. */
  public readonly test: Test;

  private deployment: DeploymentConfig;

  /**
   * Creates a new TestStack.
   *
   * @param scope - The scope in which to define this construct
   * @param id - The construct ID
   * @param props - The stack properties
   */
  constructor(scope: Construct, id: string, props: TestStackProps) {
    super(scope, id, props);

    this.deployment = props.deployment;

    // Pass the SSM parameter names so the lambda can resolve the geo-agent
    // ALB DNS and workspace bucket at runtime. This avoids any CDK dependency
    // between stacks.
    const albDnsSsmParam = `/${props.deployment.projectName}/geo-agent/lb-dns`;
    const workspaceBucketSsmParam = `/${props.deployment.projectName}/geo-agent/workspace-bucket`;

    // Create Lambda role (tests only need VPC and CloudWatch access)
    this.role = new LambdaRole(this, "GeoAgentLambdaRole", {
      account: props.deployment.account,
      roleName: "GeoAgentLambdaRole",
      existingLambdaRole: props.existingLambdaRole
    });

    // Create test Lambda function
    this.test = new Test(this, "GeoAgentIntegTest", {
      account: props.deployment.account,
      vpc: props.vpc,
      lambdaRole: this.role.lambdaRole,
      securityGroup: props.securityGroup,
      serviceEndpointSsmParam: albDnsSsmParam,
      workspaceBucketSsmParam: workspaceBucketSsmParam,
      config: this.deployment.testConfig
    });
  }
}
