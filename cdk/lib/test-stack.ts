/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
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
  /** The ALB DNS name for the MCP server. */
  albDnsName: string;
  /** The workspace S3 bucket name for test dataset uploads. */
  workspaceBucketName: string;
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
      albDnsName: props.albDnsName,
      workspaceBucketName: props.workspaceBucketName,
      config: this.deployment.testConfig
    });
  }
}
