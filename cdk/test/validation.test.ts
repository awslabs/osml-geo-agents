/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { validateProps } from "../lib/osml-geo-agent-stack";

describe("OSMLGeoAgentStack Validation", () => {
  describe("VPC ID Validation", () => {
    test("should accept valid VPC ID", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "valid-bucket-name"
        });
      }).not.toThrow();
    });

    test("should reject invalid VPC ID format", () => {
      expect(() => {
        validateProps({
          targetVpcId: "invalid-vpc-id",
          workspaceBucketName: "valid-bucket-name"
        });
      }).toThrow("Invalid VPC ID format: invalid-vpc-id");
    });

    test("should reject VPC ID without vpc- prefix", () => {
      expect(() => {
        validateProps({
          targetVpcId: "12345678",
          workspaceBucketName: "valid-bucket-name"
        });
      }).toThrow("Invalid VPC ID format: 12345678");
    });

    test("should reject VPC ID with wrong character set", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-1234567g", // 'g' is not valid hex
          workspaceBucketName: "valid-bucket-name"
        });
      }).toThrow("Invalid VPC ID format: vpc-1234567g");
    });

    test("should reject VPC ID that is too short", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-123", // too short
          workspaceBucketName: "valid-bucket-name"
        });
      }).toThrow("Invalid VPC ID format: vpc-123");
    });

    test("should reject VPC ID that is too long", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-1234567890123456789", // too long
          workspaceBucketName: "valid-bucket-name"
        });
      }).toThrow("Invalid VPC ID format: vpc-1234567890123456789");
    });
  });

  describe("S3 Bucket Name Validation", () => {
    test("should accept valid S3 bucket name", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "valid-bucket-name"
        });
      }).not.toThrow();
    });

    test("should accept S3 bucket name with dots", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "valid.bucket.name"
        });
      }).not.toThrow();
    });

    test("should reject S3 bucket name that is too short", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "ab" // too short
        });
      }).toThrow("Invalid S3 bucket name length: ab");
    });

    test("should reject S3 bucket name that is too long", () => {
      const longName = "a".repeat(64); // 64 characters, too long
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: longName
        });
      }).toThrow("Invalid S3 bucket name length: " + longName);
    });

    test("should reject S3 bucket name starting with dot", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: ".invalid-bucket"
        });
      }).toThrow("Invalid S3 bucket name format: .invalid-bucket");
    });

    test("should reject S3 bucket name ending with dot", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "invalid-bucket."
        });
      }).toThrow("Invalid S3 bucket name format: invalid-bucket.");
    });

    test("should reject S3 bucket name with uppercase letters", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "Invalid-Bucket"
        });
      }).toThrow("Invalid S3 bucket name format: Invalid-Bucket");
    });

    test("should reject S3 bucket name with consecutive dots", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "invalid..bucket"
        });
      }).toThrow("Invalid S3 bucket name: invalid..bucket");
    });

    test("should reject S3 bucket name with dot adjacent to hyphen", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "invalid.-bucket"
        });
      }).toThrow("Invalid S3 bucket name: invalid.-bucket");
    });
  });

  describe("Combined Validation", () => {
    test("should accept valid configuration", () => {
      expect(() => {
        validateProps({
          targetVpcId: "vpc-12345678",
          workspaceBucketName: "valid-bucket-name"
        });
      }).not.toThrow();
    });

    test("should reject configuration with both invalid VPC ID and bucket name", () => {
      expect(() => {
        validateProps({
          targetVpcId: "invalid-vpc",
          workspaceBucketName: "invalid-bucket."
        });
      }).toThrow("Invalid VPC ID format: invalid-vpc");
    });
  });
});
