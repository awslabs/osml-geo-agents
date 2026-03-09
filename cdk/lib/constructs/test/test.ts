/*
 * Copyright 2025-2026 Amazon.com, Inc. or its affiliates.
 */

/**
 * @file Test construct for deploying integration test Lambda.
 *
 * This construct includes:
 * - Docker image containing integration tests
 * - Lambda function that executes the tests
 * - Configuration for test execution
 */

import { Duration, RemovalPolicy, SymlinkFollowMode } from "aws-cdk-lib";
import { ISecurityGroup, IVpc } from "aws-cdk-lib/aws-ec2";
import { IRole } from "aws-cdk-lib/aws-iam";
import { DockerImageCode, DockerImageFunction } from "aws-cdk-lib/aws-lambda";
import { LogGroup, RetentionDays } from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import { writeFileSync } from "fs";
import { join } from "path";

import { BaseConfig, ConfigType, OSMLAccount } from "../types";

/**
 * Test configuration class following tile-server pattern.
 */
export class TestConfig extends BaseConfig {
  /**
   * Whether to build container resources from source.
   * @default false
   */
  public BUILD_FROM_SOURCE?: boolean;

  /**
   * The build path for the test container.
   * @default "../"
   */
  public TEST_CONTAINER_BUILD_PATH?: string;

  /**
   * The path to Dockerfile to use to build the container.
   * @default "docker/Dockerfile.integ"
   */
  public TEST_CONTAINER_DOCKERFILE?: string;

  /**
   * The Docker image to use for the test container.
   * @default "awsosml/osml-geo-agents-test:latest"
   */
  public TEST_CONTAINER_URI?: string;

  constructor(config: Partial<ConfigType> = {}) {
    const mergedConfig = {
      BUILD_FROM_SOURCE: false,
      TEST_CONTAINER_BUILD_PATH: "../",
      TEST_CONTAINER_DOCKERFILE: "docker/Dockerfile.integ",
      TEST_CONTAINER_URI: "awsosml/osml-geo-agents-test:latest",
      ...config
    };
    super(mergedConfig);
  }
}

/**
 * Properties for Test construct.
 */
export interface TestProps {
  /** The OSML account configuration. */
  readonly account: OSMLAccount;
  /** The VPC configuration. */
  readonly vpc: IVpc;
  /** The Lambda execution role. */
  readonly lambdaRole: IRole;
  /** Optional security group for Lambda. */
  readonly securityGroup?: ISecurityGroup;
  /** The SSM parameter name containing the MCP server ALB DNS. */
  readonly serviceEndpointSsmParam: string;
  /** The SSM parameter name containing the workspace S3 bucket name. */
  readonly workspaceBucketSsmParam: string;
  /** The test configuration. */
  readonly config?: TestConfig;
}

/**
 * Test construct that creates Lambda function for integration tests.
 */
export class Test extends Construct {
  /**
   * The docker image containing the integration tests.
   */
  public testImageCode: DockerImageCode;

  /**
   * The Lambda function that executes the integration tests.
   */
  public testingRunner: DockerImageFunction;

  /**
   * Configuration options for Test.
   */
  public config: TestConfig;

  /**
   * Creates a new Test construct.
   *
   * @param scope - The scope in which to define this construct
   * @param id - The construct ID
   * @param props - The construct properties
   */
  constructor(scope: Construct, id: string, props: TestProps) {
    super(scope, id);

    // Check if a custom configuration was provided
    if (props.config instanceof TestConfig) {
      this.config = props.config;
    } else {
      // Create a new default configuration
      this.config = new TestConfig(
        (props.config as unknown as Partial<ConfigType>) ?? {}
      );
    }

    this.testImageCode = this.createTestingImage();
    this.testingRunner = this.createTestingRunner(props);
  }

  /**
   * Creates the Docker image for testing.
   *
   * @returns The Docker image code
   */
  private createTestingImage(): DockerImageCode {
    if (this.config.BUILD_FROM_SOURCE) {
      // Build from source using Docker
      return DockerImageCode.fromImageAsset(
        this.config.TEST_CONTAINER_BUILD_PATH!,
        {
          file: this.config.TEST_CONTAINER_DOCKERFILE!,
          followSymlinks: SymlinkFollowMode.ALWAYS
        }
      );
    } else {
      // Use pre-built image from registry
      const tmpDockerfile = join(__dirname, "Dockerfile.tmp");
      writeFileSync(tmpDockerfile, `FROM ${this.config.TEST_CONTAINER_URI!}`);
      return DockerImageCode.fromImageAsset(__dirname, {
        file: "Dockerfile.tmp",
        followSymlinks: SymlinkFollowMode.ALWAYS
      });
    }
  }

  /**
   * Creates the Lambda function for running tests.
   *
   * @param props - The construct properties
   * @returns The Lambda function
   */
  private createTestingRunner(props: TestProps): DockerImageFunction {
    const logGroup = new LogGroup(this, "GeoAgentTestRunnerLogGroup", {
      logGroupName: "/aws/lambda/GeoAgentTestRunner",
      retention: RetentionDays.ONE_MONTH,
      removalPolicy: RemovalPolicy.DESTROY // Test logs are safe to remove
    });

    const runner = new DockerImageFunction(this, "GeoAgentTestRunner", {
      code: this.testImageCode,
      vpc: props.vpc,
      role: props.lambdaRole,
      timeout: Duration.minutes(10),
      memorySize: 1024,
      functionName: "GeoAgentTestRunner",
      securityGroups: props.securityGroup ? [props.securityGroup] : [],
      logGroup: logGroup,
      environment: {
        MCP_ENDPOINT_SSM_PARAM: props.serviceEndpointSsmParam,
        WORKSPACE_BUCKET_SSM_PARAM: props.workspaceBucketSsmParam,
        LOG_LEVEL: "INFO",
        PYTHONUNBUFFERED: "1"
      }
    });

    return runner;
  }
}
