/**
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

/**
 * Utility to load and validate the deployment configuration file.
 *
 * This module provides a strongly typed interface for reading the `deployment.json`
 * configuration, performing required validations, and returning a structured result.
 *
 * Expected structure of `deployment.json`:
 * ```json
 * {
 *   "projectName": "example-stack",
 *   "account": {
 *     "id": "123456789012",
 *     "region": "us-west-2",
 *     "isProd": true|false
 *   },
 *   "config": {
 *     "targetVpcId": "vpc-abc123",
 *     "workspaceBucketName": "my-bucket-name"
 *   }
 * }
 * ```
 *
 * @packageDocumentation
 */

import { existsSync, readFileSync } from "fs";
import { join } from "path";

import { NetworkConfig } from "../../lib/constructs/geo-agent/network";

/**
 * Represents the structure of the deployment configuration file.
 */
export interface DeploymentConfig {
  /** Logical name of the project, used for the CDK stack ID. */
  projectName: string;

  /** AWS account configuration. */
  account: {
    /** AWS Account ID. */
    id: string;
    /** AWS region for deployment. */
    region: string;
    /** Whether this is a production-like environment. */
    prodLike: boolean;
    /** Whether this is an ADC (Amazon Dedicated Cloud) environment. */
    isAdc: boolean;
  };

  /** Network configuration (optional). If not provided, NetworkStack will create a new VPC. */
  networkConfig?: NetworkConfig;

  /** Custom configuration for the OSML GeoAgent stack (optional). */
  geoAgentConfig?: {
    /** The name of the S3 bucket used as a workspace (optional - will create one if not provided). */
    WORKSPACE_BUCKET_NAME?: string;
    /** Service name abbreviation for resource naming (optional). */
    SERVICE_NAME_ABBREVIATION?: string;
    /** MCP server port (optional). */
    MCP_SERVER_PORT?: number;
    /** MCP server CPU units (optional). */
    MCP_SERVER_CPU?: number;
    /** MCP server memory size in MB (optional). */
    MCP_SERVER_MEMORY_SIZE?: number;
    /** API Gateway stage name (optional). */
    API_STAGE_NAME?: string;
  };

  /** Whether to deploy integration test infrastructure (optional). */
  deployIntegrationTests?: boolean;

  /** Test configuration (optional). */
  testConfig?: TestConfig;
}

/**
 * Test configuration for integration tests.
 */
export interface TestConfig {
  /** Whether to build test container from source. */
  BUILD_FROM_SOURCE?: boolean;
  /** URI of pre-built test container image. */
  TEST_CONTAINER_URI?: string;
  /** Path to test container build directory. */
  TEST_CONTAINER_BUILD_PATH?: string;
  /** Path to Dockerfile for test container. */
  TEST_CONTAINER_DOCKERFILE?: string;
}

/**
 * Validation error class for deployment configuration issues.
 */
class DeploymentConfigError extends Error {
  /**
   * Creates a new DeploymentConfigError.
   *
   * @param message - The error message
   * @param field - Optional field name that caused the error
   */
  constructor(
    message: string,
    // eslint-disable-next-line no-unused-vars
    public field?: string
  ) {
    super(message);
    this.name = "DeploymentConfigError";
  }
}

/**
 * Validates and trims a string field, checking for required value and whitespace.
 *
 * @param value - The value to validate
 * @param fieldName - The name of the field being validated (for error messages)
 * @param isRequired - Whether the field is required (default: true)
 * @returns The trimmed string value
 * @throws {DeploymentConfigError} If validation fails
 */
function validateStringField(
  value: unknown,
  fieldName: string,
  isRequired: boolean = true
): string {
  if (value === undefined || value === null) {
    if (isRequired) {
      throw new DeploymentConfigError(
        `Missing required field: ${fieldName}`,
        fieldName
      );
    }
    return "";
  }

  if (typeof value !== "string") {
    throw new DeploymentConfigError(
      `Field '${fieldName}' must be a string, got ${typeof value}`,
      fieldName
    );
  }

  const trimmed = value.trim();
  if (isRequired && trimmed === "") {
    throw new DeploymentConfigError(
      `Field '${fieldName}' cannot be empty or contain only whitespace`,
      fieldName
    );
  }

  return trimmed;
}

/**
 * Validates a boolean field, checking for correct type.
 *
 * @param value - The value to validate
 * @param fieldName - The name of the field being validated (for error messages)
 * @param isRequired - Whether the field is required (default: true)
 * @param defaultValue - Default value to return if field is not provided and not required
 * @returns The validated boolean value
 * @throws {DeploymentConfigError} If validation fails
 */
function validateBooleanField(
  value: unknown,
  fieldName: string,
  isRequired: boolean = true,
  defaultValue?: boolean
): boolean {
  if (value === undefined || value === null) {
    if (isRequired) {
      throw new DeploymentConfigError(
        `Missing required field: ${fieldName}`,
        fieldName
      );
    }
    return defaultValue ?? false;
  }

  if (typeof value !== "boolean") {
    throw new DeploymentConfigError(
      `Field '${fieldName}' must be a boolean, got ${typeof value}`,
      fieldName
    );
  }

  return value;
}

/**
 * Validates AWS account ID format.
 *
 * @param accountId - The account ID to validate
 * @returns The validated account ID
 * @throws {DeploymentConfigError} If the account ID format is invalid
 */
function validateAccountId(accountId: string): string {
  if (!/^\d{12}$/.test(accountId)) {
    throw new DeploymentConfigError(
      `Invalid AWS account ID format: '${accountId}'. Must be exactly 12 digits.`,
      "account.id"
    );
  }
  return accountId;
}

/**
 * Validates AWS region format using pattern matching.
 *
 * @param region - The region to validate
 * @returns The validated region
 * @throws {DeploymentConfigError} If the region format is invalid
 */
function validateRegion(region: string): string {
  // AWS region pattern: letters/numbers, hyphen, letters/numbers, optional hyphen and numbers
  if (!/^[a-z0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*$/.test(region)) {
    throw new DeploymentConfigError(
      `Invalid AWS region format: '${region}'. Must follow pattern like 'us-east-1', 'eu-west-2', etc.`,
      "account.region"
    );
  }
  return region;
}

/**
 * Validates VPC ID format.
 *
 * @param vpcId - The VPC ID to validate
 * @returns The validated VPC ID
 * @throws {DeploymentConfigError} If the VPC ID format is invalid
 */
function validateVpcId(vpcId: string): string {
  if (!/^vpc-[a-f0-9]{8}(?:[a-f0-9]{9})?$/.test(vpcId)) {
    throw new DeploymentConfigError(
      `Invalid VPC ID format: '${vpcId}'. Must start with 'vpc-' followed by 8 or 17 hexadecimal characters.`,
      "config.targetVpcId"
    );
  }
  return vpcId;
}

/**
 * Validates security group ID format.
 *
 * @param securityGroupId - The security group ID to validate
 * @returns The validated security group ID
 * @throws {DeploymentConfigError} If the security group ID format is invalid
 */
function validateSecurityGroupId(securityGroupId: string): string {
  if (!/^sg-[a-f0-9]{8}(?:[a-f0-9]{9})?$/.test(securityGroupId)) {
    throw new DeploymentConfigError(
      `Invalid security group ID format: '${securityGroupId}'. Must start with 'sg-' followed by 8 or 17 hexadecimal characters.`,
      "networkConfig.SECURITY_GROUP_ID"
    );
  }
  return securityGroupId;
}

/**
 * Validates subnet ID format.
 *
 * @param subnetId - The subnet ID to validate
 * @returns The validated subnet ID
 * @throws {DeploymentConfigError} If the subnet ID format is invalid
 */
function validateSubnetId(subnetId: string): string {
  if (!/^subnet-[a-f0-9]{8}(?:[a-f0-9]{9})?$/.test(subnetId)) {
    throw new DeploymentConfigError(
      `Invalid Subnet ID format: '${subnetId}'. Must start with 'subnet-' followed by 8 or 17 hexadecimal characters.`,
      "networkConfig.TARGET_SUBNETS"
    );
  }
  return subnetId;
}

/**
 * Validates S3 bucket name format.
 *
 * @param bucketName - The bucket name to validate
 * @returns The validated bucket name
 * @throws {DeploymentConfigError} If the bucket name format is invalid
 */
function validateBucketName(bucketName: string): string {
  if (bucketName.length < 3 || bucketName.length > 63) {
    throw new DeploymentConfigError(
      `Invalid S3 bucket name length: '${bucketName}'. Must be between 3 and 63 characters.`,
      "config.workspaceBucketName"
    );
  }

  if (!/^[a-z0-9][a-z0-9.-]*[a-z0-9]$/.test(bucketName)) {
    throw new DeploymentConfigError(
      `Invalid S3 bucket name format: '${bucketName}'. Must contain only lowercase letters, numbers, dots, and hyphens, and cannot start or end with a hyphen or dot.`,
      "config.workspaceBucketName"
    );
  }

  if (
    bucketName.includes("..") ||
    bucketName.includes(".-") ||
    bucketName.includes("-.")
  ) {
    throw new DeploymentConfigError(
      `Invalid S3 bucket name: '${bucketName}'. Cannot contain consecutive dots or dots adjacent to hyphens.`,
      "config.workspaceBucketName"
    );
  }

  return bucketName;
}

/**
 * Loads and validates the deployment configuration from `deployment/deployment.json`.
 *
 * @returns A validated {@link DeploymentConfig} object
 * @throws {DeploymentConfigError} If the file is missing, malformed, or contains invalid values
 */
export function loadDeploymentConfig(): DeploymentConfig {
  const deploymentPath = join(__dirname, "deployment.json");

  if (!existsSync(deploymentPath)) {
    throw new DeploymentConfigError(
      `Missing deployment.json file at ${deploymentPath}. Please create it by copying deployment.json.example`
    );
  }

  let parsed: unknown;
  try {
    const rawContent = readFileSync(deploymentPath, "utf-8");
    parsed = JSON.parse(rawContent) as unknown;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new DeploymentConfigError(
        `Invalid JSON format in deployment.json: ${error.message}`
      );
    }
    throw new DeploymentConfigError(
      `Failed to read deployment.json: ${error instanceof Error ? error.message : "Unknown error"}`
    );
  }

  // Validate top-level structure
  if (!parsed || typeof parsed !== "object") {
    throw new DeploymentConfigError(
      "deployment.json must contain a valid JSON object"
    );
  }

  // Cast to a record type for property access
  const config = parsed as Record<string, unknown>;

  // Validate project name
  const projectName = validateStringField(
    config.projectName,
    "projectName",
    true
  );
  if (projectName.length === 0) {
    throw new DeploymentConfigError("projectName cannot be empty");
  }

  // Validate account section
  if (!config.account || typeof config.account !== "object") {
    throw new DeploymentConfigError(
      "Missing or invalid account section in deployment.json",
      "account"
    );
  }

  const account = config.account as Record<string, unknown>;

  const accountId = validateAccountId(
    validateStringField(account.id, "account.id", true)
  );
  const region = validateRegion(
    validateStringField(account.region, "account.region", true)
  );

  const prodLike = validateBooleanField(
    account.prodLike,
    "account.prodLike",
    false,
    false
  );

  const isAdc = validateBooleanField(
    account.isAdc,
    "account.isAdc",
    false,
    false
  );

  // Parse and validate network configuration
  let networkConfig: DeploymentConfig["networkConfig"] = undefined;
  if (config.networkConfig && typeof config.networkConfig === "object") {
    const networkConfigRaw = config.networkConfig as Record<string, unknown>;

    // Validate VPC ID if provided
    let vpcId: string | undefined = undefined;
    if (
      networkConfigRaw.VPC_ID !== undefined &&
      networkConfigRaw.VPC_ID !== null
    ) {
      vpcId = validateVpcId(
        validateStringField(networkConfigRaw.VPC_ID, "networkConfig.VPC_ID")
      );
    }

    // Validate target subnets if provided
    let targetSubnets: string[] | undefined = undefined;
    if (
      networkConfigRaw.TARGET_SUBNETS !== undefined &&
      networkConfigRaw.TARGET_SUBNETS !== null
    ) {
      if (!Array.isArray(networkConfigRaw.TARGET_SUBNETS)) {
        throw new DeploymentConfigError(
          "Field 'networkConfig.TARGET_SUBNETS' must be an array",
          "networkConfig.TARGET_SUBNETS"
        );
      }

      targetSubnets = networkConfigRaw.TARGET_SUBNETS.map(
        (subnetId: unknown, index: number) =>
          validateSubnetId(
            validateStringField(
              subnetId,
              `networkConfig.TARGET_SUBNETS[${index}]`
            )
          )
      );
    }

    // Validate security group ID if provided
    let securityGroupId: string | undefined = undefined;
    if (
      networkConfigRaw.SECURITY_GROUP_ID !== undefined &&
      networkConfigRaw.SECURITY_GROUP_ID !== null
    ) {
      securityGroupId = validateSecurityGroupId(
        validateStringField(
          networkConfigRaw.SECURITY_GROUP_ID,
          "networkConfig.SECURITY_GROUP_ID"
        )
      );
    }

    // Validate that TARGET_SUBNETS is required when VPC_ID is provided
    if (vpcId && (!targetSubnets || targetSubnets.length === 0)) {
      throw new DeploymentConfigError(
        "When VPC_ID is provided, TARGET_SUBNETS must also be specified with at least one subnet ID",
        "networkConfig.TARGET_SUBNETS"
      );
    }

    // Create the network config data object
    const networkConfigData: Record<string, unknown> = {};
    if (vpcId) networkConfigData.VPC_ID = vpcId;
    if (targetSubnets) networkConfigData.TARGET_SUBNETS = targetSubnets;
    if (securityGroupId) networkConfigData.SECURITY_GROUP_ID = securityGroupId;

    // Create NetworkConfig instance
    networkConfig = new NetworkConfig(networkConfigData);
  }

  // Parse optional geoAgentConfig section
  let workspaceBucketName: string | undefined;
  let serviceNameAbbreviation: string | undefined;
  let mcpServerPort: number | undefined;
  let mcpServerCpu: number | undefined;
  let mcpServerMemorySize: number | undefined;
  let apiStageName: string | undefined;

  if (config.geoAgentConfig && typeof config.geoAgentConfig === "object") {
    const geoAgentConfigRaw = config.geoAgentConfig as Record<string, unknown>;

    // WORKSPACE_BUCKET_NAME is optional - stack will create one if not provided
    if (geoAgentConfigRaw.WORKSPACE_BUCKET_NAME !== undefined) {
      workspaceBucketName = validateBucketName(
        validateStringField(
          geoAgentConfigRaw.WORKSPACE_BUCKET_NAME,
          "geoAgentConfig.WORKSPACE_BUCKET_NAME",
          false
        )
      );
    }

    // Validate service name abbreviation
    if (geoAgentConfigRaw.SERVICE_NAME_ABBREVIATION !== undefined) {
      serviceNameAbbreviation = validateStringField(
        geoAgentConfigRaw.SERVICE_NAME_ABBREVIATION,
        "geoAgentConfig.SERVICE_NAME_ABBREVIATION",
        false
      );
    }

    // Parse optional MCP server configuration
    if (geoAgentConfigRaw.MCP_SERVER_PORT !== undefined) {
      mcpServerPort = Number(geoAgentConfigRaw.MCP_SERVER_PORT);
      if (isNaN(mcpServerPort) || mcpServerPort <= 0) {
        throw new DeploymentConfigError(
          "geoAgentConfig.MCP_SERVER_PORT must be a positive number",
          "geoAgentConfig.MCP_SERVER_PORT"
        );
      }
    }

    if (geoAgentConfigRaw.MCP_SERVER_CPU !== undefined) {
      mcpServerCpu = Number(geoAgentConfigRaw.MCP_SERVER_CPU);
      if (isNaN(mcpServerCpu) || mcpServerCpu <= 0) {
        throw new DeploymentConfigError(
          "geoAgentConfig.MCP_SERVER_CPU must be a positive number",
          "geoAgentConfig.MCP_SERVER_CPU"
        );
      }
    }

    if (geoAgentConfigRaw.MCP_SERVER_MEMORY_SIZE !== undefined) {
      mcpServerMemorySize = Number(geoAgentConfigRaw.MCP_SERVER_MEMORY_SIZE);
      if (isNaN(mcpServerMemorySize) || mcpServerMemorySize <= 0) {
        throw new DeploymentConfigError(
          "geoAgentConfig.MCP_SERVER_MEMORY_SIZE must be a positive number",
          "geoAgentConfig.MCP_SERVER_MEMORY_SIZE"
        );
      }
    }

    if (geoAgentConfigRaw.API_STAGE_NAME !== undefined) {
      apiStageName = validateStringField(
        geoAgentConfigRaw.API_STAGE_NAME,
        "geoAgentConfig.API_STAGE_NAME",
        false
      );
    }
  }

  // Parse optional deployIntegrationTests flag
  const deployIntegrationTests = validateBooleanField(
    config.deployIntegrationTests,
    "deployIntegrationTests",
    false,
    false
  );

  // Parse optional test configuration
  let testConfig: DeploymentConfig["testConfig"] = undefined;
  if (config.testConfig && typeof config.testConfig === "object") {
    testConfig = config.testConfig as TestConfig;
  }

  // Build geoAgentConfig only if there are any values to include
  let geoAgentConfig: DeploymentConfig["geoAgentConfig"] = undefined;
  if (
    workspaceBucketName ||
    serviceNameAbbreviation ||
    mcpServerPort ||
    mcpServerCpu ||
    mcpServerMemorySize ||
    apiStageName
  ) {
    geoAgentConfig = {
      ...(workspaceBucketName && {
        WORKSPACE_BUCKET_NAME: workspaceBucketName
      }),
      ...(serviceNameAbbreviation && {
        SERVICE_NAME_ABBREVIATION: serviceNameAbbreviation
      }),
      ...(mcpServerPort && { MCP_SERVER_PORT: mcpServerPort }),
      ...(mcpServerCpu && { MCP_SERVER_CPU: mcpServerCpu }),
      ...(mcpServerMemorySize && {
        MCP_SERVER_MEMORY_SIZE: mcpServerMemorySize
      }),
      ...(apiStageName && { API_STAGE_NAME: apiStageName })
    };
  }

  const validatedConfig: DeploymentConfig = {
    projectName,
    account: {
      id: accountId,
      region: region,
      prodLike: prodLike,
      isAdc: isAdc
    },
    networkConfig,
    geoAgentConfig,
    deployIntegrationTests,
    testConfig
  };

  // Only log non-sensitive configuration details
  console.log(
    `Using environment from deployment.json: projectName=${validatedConfig.projectName}, region=${validatedConfig.account.region}`
  );

  return validatedConfig;
}
