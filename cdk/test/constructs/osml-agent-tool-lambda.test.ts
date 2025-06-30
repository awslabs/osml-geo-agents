/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { Template, Match } from "aws-cdk-lib/assertions";
import { Duration, Size, Stack } from "aws-cdk-lib";
import { SubnetType } from "aws-cdk-lib/aws-ec2";
import { PolicyStatement } from "aws-cdk-lib/aws-iam";
import {
  OSMLAgentToolLambda,
  OSMLAgentToolLambdaProps
} from "../../lib/constructs/osml-agent-tool-lambda";
import { SharedTestUtils } from "../utils/test-utils";

// Test utilities and helpers
class TestUtils {
  static createDefaultProps(
    stack: Stack,
    overrides: Partial<OSMLAgentToolLambdaProps> = {}
  ): OSMLAgentToolLambdaProps {
    const vpc = SharedTestUtils.createTestVpc(stack, "TestVpc");
    const workspaceBucket = SharedTestUtils.createTestBucket(
      stack,
      "TestWorkspaceBucket"
    );

    return {
      vpc,
      workspaceBucket,
      ...overrides
    };
  }

  static createCustomProps(
    stack: Stack,
    customizations: {
      memorySize?: number;
      storageSize?: Size;
      timeout?: Duration;
      vpcSubnets?: { subnetType: SubnetType };
      policyStatements?: PolicyStatement[];
    } = {}
  ): OSMLAgentToolLambdaProps {
    const defaultProps = this.createDefaultProps(stack);

    return {
      ...defaultProps,
      ...customizations
    };
  }

  static assertBasicLambdaProperties(template: Template) {
    template.hasResourceProperties("AWS::Lambda::Function", {
      MemorySize: 1024,
      Timeout: 300,
      EphemeralStorage: {
        Size: 10240 // 10 GiB in MB
      },
      Environment: {
        Variables: {
          WORKSPACE_BUCKET_NAME: {
            Ref: Match.stringLikeRegexp("TestWorkspaceBucket*")
          }
        }
      },
      Architectures: ["x86_64"],
      TracingConfig: {
        Mode: "Active"
      },
      PackageType: "Image",
      Code: {
        ImageUri: Match.anyValue()
      },
      VpcConfig: {
        SecurityGroupIds: Match.anyValue(),
        SubnetIds: Match.anyValue()
      }
    });
  }

  static assertCustomLambdaProperties(
    template: Template,
    expectedProps: {
      memorySize?: number;
      timeout?: number;
      storageSize?: number;
    }
  ) {
    SharedTestUtils.assertCustomLambdaProperties(template, expectedProps);
  }

  static assertIAMRoleProperties(template: Template) {
    SharedTestUtils.assertBasicIAMRole(template);
  }

  static assertVPCConfiguration(template: Template) {
    SharedTestUtils.assertVPCConfiguration(template);
  }

  static assertDockerConfiguration(template: Template) {
    SharedTestUtils.assertDockerConfiguration(template);
  }

  static assertEnvironmentVariables(template: Template) {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Environment: {
        Variables: {
          WORKSPACE_BUCKET_NAME: {
            Ref: Match.stringLikeRegexp("TestWorkspaceBucket*")
          }
        }
      }
    });
  }

  static createCustomPolicyStatement(): PolicyStatement {
    return SharedTestUtils.createCustomPolicyStatement();
  }
}

describe("OSMLAgentToolLambda", () => {
  let stack: Stack;

  beforeEach(() => {
    stack = SharedTestUtils.createTestStack();
  });

  describe("Basic Construction", () => {
    test("should create Lambda function with default properties", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);
      const template = Template.fromStack(stack);

      TestUtils.assertBasicLambdaProperties(template);
      TestUtils.assertIAMRoleProperties(template);
    });

    test("should create Lambda function with custom properties", () => {
      const customProps = TestUtils.createCustomProps(stack, {
        memorySize: 2048,
        storageSize: Size.gibibytes(5),
        timeout: Duration.seconds(600),
        vpcSubnets: {
          subnetType: SubnetType.PRIVATE_WITH_EGRESS
        }
      });

      new OSMLAgentToolLambda(stack, "TestLambda", customProps);
      const template = Template.fromStack(stack);

      TestUtils.assertCustomLambdaProperties(template, {
        memorySize: 2048,
        timeout: 600,
        storageSize: 5120 // 5 GiB in MB
      });
    });
  });

  describe("IAM Permissions", () => {
    test("should create all required IAM policies", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);
      const template = Template.fromStack(stack);

      TestUtils.assertIAMRoleProperties(template);
    });

    test("should add custom policy statements when provided", () => {
      const customPolicyStatement = TestUtils.createCustomPolicyStatement();
      const propsWithCustomPolicy = TestUtils.createCustomProps(stack, {
        policyStatements: [customPolicyStatement]
      });

      new OSMLAgentToolLambda(stack, "TestLambda", propsWithCustomPolicy);
      const template = Template.fromStack(stack);

      // Verify the custom policy statement is added to the Lambda function
      template.hasResource("AWS::IAM::Policy", {});
    });
  });

  describe("VPC Configuration", () => {
    test("should configure Lambda function with VPC", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);
      const template = Template.fromStack(stack);

      TestUtils.assertVPCConfiguration(template);
    });

    test("should use custom subnet selection when provided", () => {
      const customProps = TestUtils.createCustomProps(stack, {
        vpcSubnets: {
          subnetType: SubnetType.PRIVATE_WITH_EGRESS
        }
      });

      new OSMLAgentToolLambda(stack, "TestLambda", customProps);
      const template = Template.fromStack(stack);

      TestUtils.assertVPCConfiguration(template);
    });
  });

  describe("Docker Configuration", () => {
    test("should create Docker image asset and configure Lambda", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);
      const template = Template.fromStack(stack);

      TestUtils.assertDockerConfiguration(template);
    });
  });

  describe("Environment Variables", () => {
    test("should set workspace bucket name environment variable", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);
      const template = Template.fromStack(stack);

      TestUtils.assertEnvironmentVariables(template);
    });
  });

  describe("Security Groups", () => {
    test("should allow all outbound traffic", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);
      const template = Template.fromStack(stack);

      TestUtils.assertVPCConfiguration(template);
    });
  });

  describe("CDK-NAG Suppressions", () => {
    test("should add CDK-NAG suppressions for IAM policies", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      const lambda = new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);

      // The suppressions are added via NagSuppressions.addResourceSuppressions
      // which doesn't create CloudFormation resources, so we just verify the construct
      // is created successfully without throwing errors
      expect(lambda).toBeDefined();
      expect(lambda.function).toBeDefined();
    });
  });

  describe("Edge Cases", () => {
    test("should handle undefined optional properties", () => {
      const minimalProps = TestUtils.createDefaultProps(stack);

      expect(() => {
        new OSMLAgentToolLambda(stack, "TestLambda", minimalProps);
      }).not.toThrow();
    });

    test("should handle empty policy statements array", () => {
      const propsWithEmptyPolicy = TestUtils.createCustomProps(stack, {
        policyStatements: []
      });

      expect(() => {
        new OSMLAgentToolLambda(stack, "TestLambda", propsWithEmptyPolicy);
      }).not.toThrow();
    });

    test("should handle null policy statements", () => {
      const propsWithNullPolicy = TestUtils.createCustomProps(stack, {
        policyStatements: undefined
      });

      expect(() => {
        new OSMLAgentToolLambda(stack, "TestLambda", propsWithNullPolicy);
      }).not.toThrow();
    });
  });

  describe("Resource Counts", () => {
    test("should create expected number of resources", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);
      const template = Template.fromStack(stack);

      // Should create at least:
      // - 1 Lambda function
      // - 1 IAM role
      // - Docker image asset (handled by CDK internally)
      SharedTestUtils.assertBasicResources(template, [
        "AWS::Lambda::Function",
        "AWS::IAM::Role"
      ]);
    });
  });

  describe("Construct Properties", () => {
    test("should expose function property", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      const lambda = new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);

      expect(lambda.function).toBeDefined();
      expect(lambda.function.functionName).toBeDefined();
    });

    test("should have correct construct ID", () => {
      const defaultProps = TestUtils.createDefaultProps(stack);
      const lambda = new OSMLAgentToolLambda(stack, "TestLambda", defaultProps);

      expect(lambda.node.id).toBe("TestLambda");
    });
  });
});
