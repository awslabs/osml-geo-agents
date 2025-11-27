/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { App, Stack } from "aws-cdk-lib";
import { SecurityGroup, Vpc } from "aws-cdk-lib/aws-ec2";

import { OSMLAuth } from "../lib/constructs/osml-auth";
import { OSMLGeoAgentStackProps, validateProps } from "../lib/stack-props";

// Create mock resources within a test context
let validProps: OSMLGeoAgentStackProps;

describe("OSMLGeoAgentStack Validation", () => {
  beforeAll(() => {
    // Create test app and stack for resource lookup context
    const testApp = new App({});
    const testStack = new Stack(testApp, "TestStack", {
      env: { account: "123456789012", region: "us-west-2" }
    });

    const mockVpc = Vpc.fromLookup(testStack, "TestVpc", {
      vpcId: "vpc-12345678"
    });
    const mockSecurityGroup = SecurityGroup.fromSecurityGroupId(
      testStack,
      "TestSecurityGroup",
      "sg-12345678"
    );

    // Base valid properties for testing - modify as needed for specific test cases
    validProps = {
      projectName: "osml",
      prodLike: false,
      isAdc: false,
      vpc: mockVpc,
      securityGroup: mockSecurityGroup,
      workspaceBucketName: "valid-bucket-name",
      auth: {
        authority: "https://auth.example.com",
        audience: "test-audience"
      }
    };
  });
  describe("S3 Bucket Name Validation", () => {
    test("should accept valid S3 bucket name", () => {
      expect(() => {
        validateProps(validProps);
      }).not.toThrow();
    });

    test("should accept S3 bucket name with dots", () => {
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: "valid.bucket.name"
        });
      }).not.toThrow();
    });

    test("should reject S3 bucket name that is too short", () => {
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: "ab"
        });
      }).toThrow("Invalid S3 bucket name length: ab");
    });

    test("should reject S3 bucket name that is too long", () => {
      const longName = "a".repeat(64);
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: longName
        });
      }).toThrow("Invalid S3 bucket name length: " + longName);
    });

    test("should reject S3 bucket name starting with dot", () => {
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: ".invalid-bucket"
        });
      }).toThrow("Invalid S3 bucket name format: .invalid-bucket");
    });

    test("should reject S3 bucket name ending with dot", () => {
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: "invalid-bucket."
        });
      }).toThrow("Invalid S3 bucket name format: invalid-bucket.");
    });

    test("should reject S3 bucket name with uppercase letters", () => {
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: "Invalid-Bucket"
        });
      }).toThrow("Invalid S3 bucket name format: Invalid-Bucket");
    });

    test("should reject S3 bucket name with consecutive dots", () => {
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: "invalid..bucket"
        });
      }).toThrow("Invalid S3 bucket name: invalid..bucket");
    });

    test("should reject S3 bucket name with dot adjacent to hyphen", () => {
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: "invalid.-bucket"
        });
      }).toThrow("Invalid S3 bucket name: invalid.-bucket");
    });
  });

  describe("Project Name Validation", () => {
    test("should accept valid project name", () => {
      expect(() => {
        validateProps({
          ...validProps,
          projectName: "osml-geo-agents"
        });
      }).not.toThrow();
    });

    test("should reject project name too short", () => {
      expect(() => {
        validateProps({
          ...validProps,
          projectName: "a"
        });
      }).toThrow("Project name must be between 2 and 50 characters");
    });

    test("should reject project name too long", () => {
      const longName = "a".repeat(51);
      expect(() => {
        validateProps({
          ...validProps,
          projectName: longName
        });
      }).toThrow("Project name must be between 2 and 50 characters");
    });

    test("should reject project name with invalid characters", () => {
      expect(() => {
        validateProps({
          ...validProps,
          projectName: "invalid project name!"
        });
      }).toThrow(
        "Project name can only contain alphanumeric characters, hyphens, and underscores"
      );
    });

    test("should accept project name with hyphens and underscores", () => {
      expect(() => {
        validateProps({
          ...validProps,
          projectName: "valid-project_name123"
        });
      }).not.toThrow();
    });
  });

  describe("Service Name Abbreviation Validation", () => {
    test("should accept valid service name abbreviation", () => {
      expect(() => {
        validateProps({
          ...validProps,
          serviceNameAbbreviation: "GA"
        });
      }).not.toThrow();
    });

    test("should accept undefined service name abbreviation", () => {
      expect(() => {
        validateProps(validProps);
      }).not.toThrow();
    });

    test("should reject service name abbreviation too short", () => {
      expect(() => {
        validateProps({
          ...validProps,
          serviceNameAbbreviation: "A"
        });
      }).toThrow(
        "Service name abbreviation must be between 2 and 10 characters"
      );
    });

    test("should reject service name abbreviation too long", () => {
      expect(() => {
        validateProps({
          ...validProps,
          serviceNameAbbreviation: "VERYLONGNAME"
        });
      }).toThrow(
        "Service name abbreviation must be between 2 and 10 characters"
      );
    });

    test("should reject service name abbreviation with invalid characters", () => {
      expect(() => {
        validateProps({
          ...validProps,
          serviceNameAbbreviation: "GA-1"
        });
      }).toThrow(
        "Service name abbreviation can only contain alphanumeric characters"
      );
    });
  });

  describe("MCP Server Configuration Validation", () => {
    test("should accept valid CPU value", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerCpu: 2048
        });
      }).not.toThrow();
    });

    test("should reject invalid CPU value", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerCpu: 3000
        });
      }).toThrow(
        "mcpServerCpu must be one of: 256, 512, 1024, 2048, 4096, 8192, 16384"
      );
    });

    test("should accept valid memory value", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerMemorySize: 4096
        });
      }).not.toThrow();
    });

    test("should reject memory value too low", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerMemorySize: 256
        });
      }).toThrow("mcpServerMemorySize must be between 512 and 30720 MB");
    });

    test("should reject memory value too high", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerMemorySize: 40000
        });
      }).toThrow("mcpServerMemorySize must be between 512 and 30720 MB");
    });

    test("should accept valid port value", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerPort: 8080
        });
      }).not.toThrow();
    });

    test("should reject port value too low", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerPort: 0
        });
      }).toThrow("mcpServerPort must be a positive number");
    });

    test("should reject port value too high", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerPort: 70000
        });
      }).toThrow("mcpServerPort must be between 1 and 65535");
    });

    test("should accept valid CPU/memory combination", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerCpu: 2048,
          mcpServerMemorySize: 4096
        });
      }).not.toThrow();
    });

    test("should reject invalid CPU/memory combination", () => {
      expect(() => {
        validateProps({
          ...validProps,
          mcpServerCpu: 256,
          mcpServerMemorySize: 8192
        });
      }).toThrow(
        "Invalid CPU/Memory combination: 256 CPU requires memory to be one of: 512, 1024, 2048"
      );
    });
  });

  describe("API Stage Name Validation", () => {
    test("should accept valid API stage name", () => {
      expect(() => {
        validateProps({
          ...validProps,
          apiStageName: "prod"
        });
      }).not.toThrow();
    });

    test("should accept undefined API stage name", () => {
      expect(() => {
        validateProps(validProps);
      }).not.toThrow();
    });

    test("should reject API stage name too long", () => {
      const longStageName = "a".repeat(129);
      expect(() => {
        validateProps({
          ...validProps,
          apiStageName: longStageName
        });
      }).toThrow("API stage name must be between 1 and 128 characters");
    });

    test("should reject API stage name with invalid characters", () => {
      expect(() => {
        validateProps({
          ...validProps,
          apiStageName: "stage with spaces"
        });
      }).toThrow(
        "API stage name can only contain alphanumeric characters, hyphens, and underscores"
      );
    });
  });

  describe("Auth Configuration Validation", () => {
    test("should accept valid auth configuration", () => {
      expect(() => {
        validateProps(validProps);
      }).not.toThrow();
    });

    test("should reject missing auth object", () => {
      expect(() => {
        validateProps({
          ...validProps,
          auth: undefined as unknown as OSMLAuth
        });
      }).toThrow("auth configuration is required");
    });

    test("should reject auth object missing authority", () => {
      expect(() => {
        validateProps({
          ...validProps,
          auth: {
            audience: "test-audience"
          } as unknown as OSMLAuth
        });
      }).toThrow("auth.authority is required and must be a non-empty string");
    });

    test("should reject auth object missing audience", () => {
      expect(() => {
        validateProps({
          ...validProps,
          auth: {
            authority: "https://auth.example.com"
          } as unknown as OSMLAuth
        });
      }).toThrow("auth.audience is required and must be a non-empty string");
    });

    test("should reject non-HTTPS authority URL", () => {
      expect(() => {
        validateProps({
          ...validProps,
          auth: {
            authority: "http://auth.example.com",
            audience: "test-audience"
          }
        });
      }).toThrow("auth.authority should use HTTPS protocol for security");
    });

    test("should reject invalid authority URL format", () => {
      expect(() => {
        validateProps({
          ...validProps,
          auth: {
            authority: "not-a-url",
            audience: "test-audience"
          }
        });
      }).toThrow("auth.authority must be a valid URL");
    });

    test("should reject empty authority string", () => {
      expect(() => {
        validateProps({
          ...validProps,
          auth: {
            authority: "",
            audience: "test-audience"
          }
        });
      }).toThrow("auth.authority is required and must be a non-empty string");
    });

    test("should reject empty audience string", () => {
      expect(() => {
        validateProps({
          ...validProps,
          auth: {
            authority: "https://auth.example.com",
            audience: ""
          }
        });
      }).toThrow("auth.audience is required and must be a non-empty string");
    });
  });

  describe("Combined Validation", () => {
    test("should accept valid configuration", () => {
      expect(() => {
        validateProps(validProps);
      }).not.toThrow();
    });

    test("should reject configuration with invalid bucket name", () => {
      expect(() => {
        validateProps({
          ...validProps,
          workspaceBucketName: "invalid-bucket."
        });
      }).toThrow("Invalid S3 bucket name format: invalid-bucket.");
    });
  });
});
