/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { Template, Match } from "aws-cdk-lib/assertions";
import { Stack } from "aws-cdk-lib";
import { Vpc } from "aws-cdk-lib/aws-ec2";
import { Bucket } from "aws-cdk-lib/aws-s3";
import { PolicyStatement, Effect } from "aws-cdk-lib/aws-iam";

/**
 * Shared test utilities for CDK construct tests
 */
export class SharedTestUtils {
  /**
   * Creates a basic VPC for testing
   */
  static createTestVpc(stack: Stack, id: string = "TestVpc"): Vpc {
    return new Vpc(stack, id);
  }

  /**
   * Creates a basic S3 bucket for testing
   */
  static createTestBucket(stack: Stack, id: string = "TestBucket"): Bucket {
    return new Bucket(stack, id);
  }

  /**
   * Creates a basic Lambda execution role policy statement
   */
  static createBasicLambdaRolePolicy(): PolicyStatement {
    return new PolicyStatement({
      effect: Effect.ALLOW,
      actions: ["sts:AssumeRole"],
      resources: ["*"]
    });
  }

  /**
   * Creates a custom policy statement for testing
   */
  static createCustomPolicyStatement(
    actions: string[] = ["s3:GetBucketPolicy"],
    resources: string[] = ["*"]
  ): PolicyStatement {
    return new PolicyStatement({
      effect: Effect.ALLOW,
      actions,
      resources
    });
  }

  /**
   * Asserts basic IAM role properties
   */
  static assertBasicIAMRole(
    template: Template,
    service: string = "lambda.amazonaws.com"
  ) {
    template.hasResourceProperties("AWS::IAM::Role", {
      AssumeRolePolicyDocument: {
        Statement: [
          {
            Action: "sts:AssumeRole",
            Effect: "Allow",
            Principal: {
              Service: service
            }
          }
        ]
      }
    });
  }

  /**
   * Asserts basic Lambda function properties
   */
  static assertBasicLambdaFunction(template: Template) {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Architectures: ["x86_64"],
      TracingConfig: {
        Mode: "Active"
      }
    });
  }

  /**
   * Asserts VPC configuration is present
   */
  static assertVPCConfiguration(template: Template) {
    template.hasResourceProperties("AWS::Lambda::Function", {
      VpcConfig: Match.anyValue()
    });
  }

  /**
   * Asserts Docker image configuration
   */
  static assertDockerConfiguration(template: Template) {
    template.hasResourceProperties("AWS::Lambda::Function", {
      PackageType: "Image",
      Code: {
        ImageUri: Match.anyValue()
      }
    });
  }

  /**
   * Asserts environment variables are set
   */
  static assertEnvironmentVariables(
    template: Template,
    expectedVariables: Record<string, any>
  ) {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Environment: {
        Variables: expectedVariables
      }
    });
  }

  /**
   * Asserts custom Lambda properties
   */
  static assertCustomLambdaProperties(
    template: Template,
    expectedProps: {
      memorySize?: number;
      timeout?: number;
      storageSize?: number;
    }
  ) {
    const properties: any = {};

    if (expectedProps.memorySize) {
      properties.MemorySize = expectedProps.memorySize;
    }
    if (expectedProps.timeout) {
      properties.Timeout = expectedProps.timeout;
    }
    if (expectedProps.storageSize) {
      properties.EphemeralStorage = {
        Size: expectedProps.storageSize
      };
    }

    template.hasResourceProperties("AWS::Lambda::Function", properties);
  }

  /**
   * Asserts that expected resources are created
   */
  static assertBasicResources(template: Template, resourceTypes: string[]) {
    resourceTypes.forEach((resourceType) => {
      template.hasResource(resourceType, {});
    });
  }

  /**
   * Creates a test stack with common setup
   */
  static createTestStack(): Stack {
    return new Stack();
  }

  /**
   * Asserts Lambda permission properties
   */
  static assertLambdaPermission(
    template: Template,
    principal: string = "lambda.amazonaws.com",
    action: string = "lambda:InvokeFunction"
  ) {
    template.hasResourceProperties("AWS::Lambda::Permission", {
      Action: action,
      Principal: principal
    });
  }

  /**
   * Asserts Bedrock agent properties
   */
  static assertBedrockAgentProperties(
    template: Template,
    agentName: string = "TestAgent-BedrockAgent",
    foundationModel: string = "anthropic.claude-3-5-sonnet-20241022-v2:0"
  ) {
    template.hasResourceProperties("AWS::Bedrock::Agent", {
      AgentName: agentName,
      FoundationModel: foundationModel,
      IdleSessionTTLInSeconds: 1800,
      Description: Match.anyValue(),
      Instruction: Match.anyValue()
    });
  }

  /**
   * Asserts Bedrock agent alias properties
   */
  static assertBedrockAgentAlias(template: Template, aliasName: string) {
    template.hasResourceProperties("AWS::Bedrock::AgentAlias", {
      AgentAliasName: aliasName
    });
  }
}
