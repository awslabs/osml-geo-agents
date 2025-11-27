/**
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { StackProps } from "aws-cdk-lib";
import { ISecurityGroup, IVpc } from "aws-cdk-lib/aws-ec2";

import { OSMLAuth } from "./constructs/osml-auth";

/**
 * Properties for configuring the OSML Geo Agent Stack.
 * This interface defines the configuration options needed to deploy
 * the complete OSML Geo Agent infrastructure including VPC and MCP server resources.
 */
export interface OSMLGeoAgentStackProps extends StackProps {
  /**
   * The project name for resource naming and identification.
   */
  projectName: string;

  /**
   * Whether this is a production-like deployment.
   * Affects removal policies and other production-specific configurations.
   */
  prodLike: boolean;

  /**
   * Whether this is an ADC (Amazon Dedicated Cloud) environment.
   */
  isAdc: boolean;

  /**
   * Service name abbreviation for resource naming.
   * @default "GA"
   */
  serviceNameAbbreviation?: string;

  /**
   * The VPC where the agent resources will be deployed.
   * The VPC must have private subnets with egress access for the agents to function properly.
   * Passed from NetworkStack.
   */
  vpc: IVpc;

  /**
   * The security group for the MCP server resources.
   * Passed from NetworkStack.
   */
  securityGroup: ISecurityGroup;

  /**
   * The name of the S3 bucket used as a shared workspace for the MCP server.
   * This bucket stores geospatial assets and intermediate processing results.
   * If not provided, a new bucket will be created.
   * @pattern ^[a-z0-9][a-z0-9.-]*[a-z0-9]$
   * @minLength 3
   * @maxLength 63
   */
  workspaceBucketName?: string;

  /**
   * The CPU units for the MCP server ECS task.
   * @default 2048
   */
  mcpServerCpu?: number;

  /**
   * The memory size in MB for the MCP server ECS task.
   * @default 4096
   */
  mcpServerMemorySize?: number;

  /**
   * The container port for the MCP server.
   * @default 8080
   */
  mcpServerPort?: number;

  /**
   * The stage name for the API Gateway deployment.
   * @default "prod"
   */
  apiStageName?: string;

  /**
   * OSML Auth configuration for API Gateway authorization.
   * This is required - all APIs must be deployed with proper authentication.
   */
  auth: OSMLAuth;
}

/**
 * Validates that a value is a non-empty string.
 * @param value - The value to validate
 * @param fieldName - The name of the field being validated
 * @throws {Error} When validation fails
 */
const validateString = (value: unknown, fieldName: string): void => {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${fieldName} must be a non-empty string`);
  }
};

/**
 * Validates that a value is a boolean.
 * @param value - The value to validate
 * @param fieldName - The name of the field being validated
 * @throws {Error} When validation fails
 */
const validateBoolean = (value: unknown, fieldName: string): void => {
  if (typeof value !== "boolean") {
    throw new Error(`${fieldName} must be a boolean`);
  }
};

/**
 * Validates the project name.
 * @param projectName - The project name to validate
 * @throws {Error} When validation fails
 */
const validateProjectName = (projectName: string): void => {
  validateString(projectName, "projectName");

  // Project name should be reasonable length and contain valid characters
  if (projectName.length < 2 || projectName.length > 50) {
    throw new Error("Project name must be between 2 and 50 characters");
  }

  // Allow alphanumeric, hyphens, and underscores
  if (!/^[a-zA-Z0-9_-]+$/.test(projectName)) {
    throw new Error(
      "Project name can only contain alphanumeric characters, hyphens, and underscores"
    );
  }
};

/**
 * Validates the prodLike boolean flag.
 * @param prodLike - The production-like flag to validate
 * @throws {Error} When validation fails
 */
const validateProdLike = (prodLike: boolean): void => {
  validateBoolean(prodLike, "prodLike");
};

/**
 * Validates the isAdc boolean flag.
 * @param isAdc - The ADC flag to validate
 * @throws {Error} When validation fails
 */
const validateIsAdc = (isAdc: boolean): void => {
  validateBoolean(isAdc, "isAdc");
};

/**
 * Validates the service name abbreviation.
 * @param serviceNameAbbreviation - The service name abbreviation to validate
 * @throws {Error} When validation fails
 */
const validateServiceNameAbbreviation = (
  serviceNameAbbreviation?: string
): void => {
  if (serviceNameAbbreviation !== undefined) {
    validateString(serviceNameAbbreviation, "serviceNameAbbreviation");

    // Should be short abbreviation (2-10 characters)
    if (
      serviceNameAbbreviation.length < 2 ||
      serviceNameAbbreviation.length > 10
    ) {
      throw new Error(
        "Service name abbreviation must be between 2 and 10 characters"
      );
    }

    // Should be alphanumeric only
    if (!/^[a-zA-Z0-9]+$/.test(serviceNameAbbreviation)) {
      throw new Error(
        "Service name abbreviation can only contain alphanumeric characters"
      );
    }
  }
};

/**
 * Validates the S3 bucket name if provided.
 * @param workspaceBucketName - The bucket name to validate
 * @throws {Error} When validation fails
 */
const validateBucket = (workspaceBucketName?: string): void => {
  if (workspaceBucketName !== undefined) {
    validateString(workspaceBucketName, "workspaceBucketName");

    // Validate S3 bucket name length: must be 3-63 characters long
    if (workspaceBucketName.length < 3 || workspaceBucketName.length > 63) {
      throw new Error(
        `Invalid S3 bucket name length: ${workspaceBucketName}. Must be between 3 and 63 characters`
      );
    }

    // Validate S3 bucket name format: must start and end with alphanumeric characters
    // and can contain lowercase letters, numbers, hyphens, and dots
    if (!/^[a-z0-9][a-z0-9.-]*[a-z0-9]$/.test(workspaceBucketName)) {
      throw new Error(
        `Invalid S3 bucket name format: ${workspaceBucketName}. Must start and end with alphanumeric characters and contain only lowercase letters, numbers, hyphens, and dots`
      );
    }

    // Additional S3 bucket name validation rules
    if (workspaceBucketName.includes("..")) {
      throw new Error(
        `Invalid S3 bucket name: ${workspaceBucketName}. Cannot contain consecutive dots`
      );
    }

    if (
      workspaceBucketName.includes(".-") ||
      workspaceBucketName.includes("-.")
    ) {
      throw new Error(
        `Invalid S3 bucket name: ${workspaceBucketName}. Cannot contain dot-hyphen or hyphen-dot combinations`
      );
    }

    // Cannot look like an IP address
    if (/^\d+\.\d+\.\d+\.\d+$/.test(workspaceBucketName)) {
      throw new Error(
        `Invalid S3 bucket name: ${workspaceBucketName}. Cannot be formatted as an IP address`
      );
    }
  }
};

/**
 * Validates the MCP server configuration parameters.
 * @param mcpServerCpu - The CPU units for the MCP server
 * @param mcpServerMemorySize - The memory size in MB for the MCP server
 * @param mcpServerPort - The container port for the MCP server
 * @throws {Error} When validation fails
 */
const validateMcpServerConfig = (
  mcpServerCpu?: number,
  mcpServerMemorySize?: number,
  mcpServerPort?: number
): void => {
  // Validate CPU if provided
  if (mcpServerCpu !== undefined) {
    if (typeof mcpServerCpu !== "number" || mcpServerCpu <= 0) {
      throw new Error("mcpServerCpu must be a positive number");
    }

    // Valid Fargate CPU values: 256, 512, 1024, 2048, 4096, 8192, 16384
    const validCpuValues = [256, 512, 1024, 2048, 4096, 8192, 16384];
    if (!validCpuValues.includes(mcpServerCpu)) {
      throw new Error(
        `mcpServerCpu must be one of: ${validCpuValues.join(", ")}`
      );
    }
  }

  // Validate memory if provided
  if (mcpServerMemorySize !== undefined) {
    if (typeof mcpServerMemorySize !== "number" || mcpServerMemorySize <= 0) {
      throw new Error("mcpServerMemorySize must be a positive number");
    }

    // Memory should be between 512MB and 30GB for Fargate
    if (mcpServerMemorySize < 512 || mcpServerMemorySize > 30720) {
      throw new Error("mcpServerMemorySize must be between 512 and 30720 MB");
    }
  }

  // Validate port if provided
  if (mcpServerPort !== undefined) {
    if (typeof mcpServerPort !== "number" || mcpServerPort <= 0) {
      throw new Error("mcpServerPort must be a positive number");
    }

    // Port should be in valid range
    if (mcpServerPort < 1 || mcpServerPort > 65535) {
      throw new Error("mcpServerPort must be between 1 and 65535");
    }
  }

  // Validate CPU/Memory combination if both provided
  if (mcpServerCpu !== undefined && mcpServerMemorySize !== undefined) {
    const validCombinations: Record<number, number[]> = {
      256: [512, 1024, 2048],
      512: [1024, 2048, 3072, 4096],
      1024: [2048, 3072, 4096, 5120, 6144, 7168, 8192],
      2048: [
        4096, 5120, 6144, 7168, 8192, 9216, 10240, 11264, 12288, 13312, 14336,
        15360, 16384
      ],
      4096: [
        8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384, 17408,
        18432, 19456, 20480, 21504, 22528, 23552, 24576, 25600, 26624, 27648,
        28672, 29696, 30720
      ],
      8192: [16384, 20480, 24576, 28672, 30720],
      16384: [32768, 65536]
    };

    if (!validCombinations[mcpServerCpu]?.includes(mcpServerMemorySize)) {
      throw new Error(
        `Invalid CPU/Memory combination: ${mcpServerCpu} CPU requires memory to be one of: ${validCombinations[mcpServerCpu]?.join(", ") || "none valid"}`
      );
    }
  }
};

/**
 * Validates the API stage name.
 * @param apiStageName - The API stage name to validate
 * @throws {Error} When validation fails
 */
const validateApiStageName = (apiStageName?: string): void => {
  if (apiStageName !== undefined) {
    validateString(apiStageName, "apiStageName");

    // Stage name should be reasonable length
    if (apiStageName.length < 1 || apiStageName.length > 128) {
      throw new Error("API stage name must be between 1 and 128 characters");
    }

    // Should contain valid characters for API Gateway stage names
    if (!/^[a-zA-Z0-9_-]+$/.test(apiStageName)) {
      throw new Error(
        "API stage name can only contain alphanumeric characters, hyphens, and underscores"
      );
    }
  }
};

/**
 * Validates the OSML Auth configuration.
 * @param auth - The OSML Auth configuration to validate
 * @throws {Error} When validation fails
 */
const validateAuth = (auth: OSMLAuth): void => {
  if (!auth) {
    throw new Error("auth configuration is required");
  }

  // The auth object should be a valid object
  if (typeof auth !== "object") {
    throw new Error("auth must be a valid OSMLAuth object");
  }

  const authObj = auth as unknown as Record<string, unknown>; // Validating unknown input, can't assume OSMLAuth interface

  // Check that auth has the required authority field
  if (
    !("authority" in authObj) ||
    typeof authObj.authority !== "string" ||
    authObj.authority.trim().length === 0
  ) {
    throw new Error(
      "auth.authority is required and must be a non-empty string"
    );
  }

  // Check that auth has the required audience field
  if (
    !("audience" in authObj) ||
    typeof authObj.audience !== "string" ||
    authObj.audience.trim().length === 0
  ) {
    throw new Error("auth.audience is required and must be a non-empty string");
  }

  // Validate that authority looks like a URL
  try {
    new URL(authObj.authority);
  } catch {
    throw new Error(
      `auth.authority must be a valid URL, got: ${authObj.authority}`
    );
  }

  // Validate that authority uses HTTPS (security best practice for IdP)
  if (!authObj.authority.startsWith("https://")) {
    throw new Error(
      `auth.authority should use HTTPS protocol for security, got: ${authObj.authority}`
    );
  }
};

/**
 * Validates the configuration properties for the OSML Geo Agent Stack.
 *
 * This function performs input validation to ensure that the provided configuration
 * meets AWS requirements and follows proper naming conventions before deploying
 * the infrastructure. It validates all required and optional parameters using
 * individual validation functions for better maintainability and error reporting.
 *
 * @param {OSMLGeoAgentStackProps} props - The configuration properties to validate
 * @throws {Error} When validation fails with a descriptive error message
 */
export const validateProps = (props: OSMLGeoAgentStackProps): void => {
  try {
    // Validate required properties
    validateProjectName(props.projectName);
    validateProdLike(props.prodLike);
    validateIsAdc(props.isAdc);
    validateAuth(props.auth);

    // Validate optional properties
    validateServiceNameAbbreviation(props.serviceNameAbbreviation);
    validateBucket(props.workspaceBucketName);
    validateMcpServerConfig(
      props.mcpServerCpu,
      props.mcpServerMemorySize,
      props.mcpServerPort
    );
    validateApiStageName(props.apiStageName);
  } catch (error) {
    throw new Error(
      `OSML Geo Agent Stack validation failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }
};
