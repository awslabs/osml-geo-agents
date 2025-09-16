/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { Duration } from "aws-cdk-lib";
import {
  SecurityGroup,
  IVpc,
  SubnetSelection,
  ISecurityGroup
} from "aws-cdk-lib/aws-ec2";
import { IRole } from "aws-cdk-lib/aws-iam";
import { Code, Function, Runtime } from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";

import { OSMLAuth } from "./osml-auth";

/**
 * Represents the properties required to configure the OSMLAuthorizer Construct.
 * @interface
 */
export interface OSMLAuthorizerProps {
  /**
   * The configuration for the authentication.
   *
   * @type {OSMLAuth}
   */
  auth: OSMLAuth;

  /**
   * The name of the service
   *
   * @type {string}
   */
  name: string;

  /**
   * The VPC in which the authorizer function will be deployed.
   * @type {IVpc}
   */
  vpc: IVpc;

  /**
   * The subnets in which the authorizer function will be deployed.
   * @type {SubnetSelection}
   */
  vpcSubnets: SubnetSelection;

  /**
   * The optional security group ID to use for this resource.
   * @type {string}
   */
  securityGroupId?: string;

  /**
   * The optional IAM role for the Lambda function.
   */
  lambdaRole?: IRole;
}

/**
 * Represents the construct that creates Authorizer Lambda function
 */
export class OSMLAuthorizer extends Construct {
  /**
   * The Lambda function used as the Authorizer.
   * @type {Function}
   */
  public authorizerFunction: Function;

  /**
   * The security group associated with the Authorizer function.
   * @type {ISecurityGroup}
   */
  public securityGroup: ISecurityGroup;

  /**
   * Creates an instance of OSMLAuthorizer Lambda Function
   * @param {Construct} scope - The scope/stack in which to define this construct.
   * @param {string} id - The unique id of the construct within current scope.
   * @param {OSMLAuthorizerProps} props - The properties of this construct.
   */
  constructor(scope: Construct, id: string, props: OSMLAuthorizerProps) {
    super(scope, id);

    // Create security group for the authorizer function
    this.securityGroup = props.securityGroupId
      ? SecurityGroup.fromSecurityGroupId(
          this,
          "AuthorizerImportSecurityGroup",
          props.securityGroupId
        )
      : new SecurityGroup(this, "AuthorizerSecurityGroup", {
          vpc: props.vpc,
          description: "Security group for OSML Authorizer Lambda function",
          allowAllOutbound: true
        });

    this.authorizerFunction = new Function(this, `AuthorizerFunction${id}`, {
      functionName: `${props.name}-AuthorizerFunction`,
      runtime: Runtime.PYTHON_3_13,
      vpc: props.vpc,
      securityGroups: [this.securityGroup],
      vpcSubnets: props.vpcSubnets,
      role: props.lambdaRole,
      timeout: Duration.seconds(30),
      memorySize: 256,
      code: Code.fromAsset("lambda/authorizer", {
        bundling: {
          image: Runtime.PYTHON_3_13.bundlingImage,
          command: [
            "/bin/bash",
            "-c",
            "pip install pyjwt requests cryptography -t /asset-output && cp -au . /asset-output"
          ]
        }
      }),
      handler: "lambda_function.lambda_handler",
      environment: {
        AUTHORITY: props.auth ? props.auth.authority : "",
        AUDIENCE: props.auth ? props.auth.audience : ""
      }
    });
  }
}
