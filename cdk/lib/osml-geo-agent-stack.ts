/*
 * Copyright 2025-2026 Amazon.com, Inc. or its affiliates.
 */

import { Duration, RemovalPolicy, Stack } from "aws-cdk-lib";
import { SubnetType } from "aws-cdk-lib/aws-ec2";
import { Platform } from "aws-cdk-lib/aws-ecr-assets";
import {
  AwsLogDriver,
  AwsLogDriverMode,
  Cluster,
  ContainerImage,
  ContainerInsights,
  FargateTaskDefinition,
  Protocol as EcsProtocol
} from "aws-cdk-lib/aws-ecs";
import { ApplicationLoadBalancedFargateService } from "aws-cdk-lib/aws-ecs-patterns";
import {
  ApplicationLoadBalancer,
  Protocol as ElbProtocol
} from "aws-cdk-lib/aws-elasticloadbalancingv2";
import {
  Effect,
  PolicyDocument,
  PolicyStatement,
  Role,
  ServicePrincipal
} from "aws-cdk-lib/aws-iam";
import { LogGroup, RetentionDays } from "aws-cdk-lib/aws-logs";
import { Bucket, BucketEncryption, IBucket } from "aws-cdk-lib/aws-s3";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";
import { join } from "path";

// Local OSML constructs
import { nagSuppressions } from "./nag-suppressions";
import { OSMLGeoAgentStackProps, validateProps } from "./stack-props";

/**
 * CDK Stack that deploys the OSML Geo Agent MCP Server infrastructure.
 *
 * This stack creates a geospatial MCP (Model Context Protocol) server system that provides
 * geospatial analysis tools. The system includes:
 *
 * - An ECS Fargate service running the containerized MCP server
 * - An Application Load Balancer for traffic routing within the VPC
 * - S3 bucket for workspace storage (created if not provided)
 * - Proper IAM permissions and VPC configuration
 *
 * The MCP server runs within a private VPC using ECS Fargate for persistent connections
 * and uses S3 workspace storage for geospatial assets. Access is restricted to within
 * the VPC, with no public internet exposure.
 */
export class OSMLGeoAgentStack extends Stack {
  /**
   * The ECS cluster for the MCP server.
   */
  public readonly cluster: Cluster;

  /**
   * The Fargate service for the MCP server.
   */
  public readonly fargateService: ApplicationLoadBalancedFargateService;

  /**
   * The Application Load Balancer for the MCP server.
   */
  public readonly alb: ApplicationLoadBalancer;

  /**
   * The workspace S3 bucket.
   */
  public readonly workspaceBucket: IBucket;

  /**
   * Creates a new instance of the OSML Geo Agent Stack.
   *
   * This constructor sets up the complete infrastructure for the OSML Geo Agent MCP server,
   * including the ECS Fargate service, Application Load Balancer, S3 workspace, and proper networking and permissions.
   *
   * @param { Construct } scope - The construct scope in which to create the stack
   * @param { string } id - The unique identifier for this stack
   * @param { OSMLGeoAgentStackProps } props - Configuration properties including VPC and optional workspace bucket name
   */
  constructor(scope: Construct, id: string, props: OSMLGeoAgentStackProps) {
    super(scope, id, props);

    // Validate the configuration properties before proceeding
    validateProps(props);

    // Set default values
    const serviceNameAbbreviation = props.serviceNameAbbreviation || "GA";
    const mcpServerCpu = props.mcpServerCpu || 2048;
    const mcpServerMemorySize = props.mcpServerMemorySize || 4096;
    const mcpServerPort = props.mcpServerPort || 8080;

    // Use VPC and SecurityGroup passed from NetworkStack
    const vpc = props.vpc;

    // Determine removal policy based on production-like flag
    const removalPolicy = props.prodLike
      ? RemovalPolicy.RETAIN
      : RemovalPolicy.DESTROY;

    // Create or reference the workspace bucket
    if (props.workspaceBucketName) {
      // Use existing bucket
      this.workspaceBucket = Bucket.fromBucketName(
        this,
        `${serviceNameAbbreviation}-WorkspaceBucket`,
        props.workspaceBucketName
      );
    } else {
      // Create new bucket
      this.workspaceBucket = new Bucket(
        this,
        `${serviceNameAbbreviation}-WorkspaceBucket`,
        {
          bucketName: `${props.projectName.toLowerCase()}-geo-agent-${this.account}-${this.region}`,
          encryption: BucketEncryption.S3_MANAGED,
          removalPolicy: removalPolicy,
          versioned: false,
          publicReadAccess: false,
          blockPublicAccess: {
            blockPublicAcls: true,
            blockPublicPolicy: true,
            ignorePublicAcls: true,
            restrictPublicBuckets: true
          }
        }
      );
    }

    // Create log group for the container
    const logGroup = new LogGroup(
      this,
      `${serviceNameAbbreviation}-MCPServerLogGroup`,
      {
        logGroupName: `/aws/ecs/${props.projectName}-${serviceNameAbbreviation}-MCPServer`,
        retention: RetentionDays.TWO_WEEKS,
        removalPolicy: removalPolicy
      }
    );

    // Create IAM roles for ECS task and execution
    const mcpServerTaskRole = new Role(
      this,
      `${serviceNameAbbreviation}-MCPServerTaskRole`,
      {
        assumedBy: new ServicePrincipal("ecs-tasks.amazonaws.com"),
        inlinePolicies: {
          S3WorkspaceAccess: new PolicyDocument({
            statements: [
              new PolicyStatement({
                effect: Effect.ALLOW,
                actions: ["s3:ListBucket", "s3:GetBucketLocation"],
                resources: [this.workspaceBucket.bucketArn]
              }),
              new PolicyStatement({
                effect: Effect.ALLOW,
                actions: ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                resources: [`${this.workspaceBucket.bucketArn}/*`]
              })
            ]
          })
        }
      }
    );

    const mcpServerExecutionRole = new Role(
      this,
      `${serviceNameAbbreviation}-MCPServerExecutionRole`,
      {
        assumedBy: new ServicePrincipal("ecs-tasks.amazonaws.com"),
        inlinePolicies: {
          ECSTaskExecution: new PolicyDocument({
            statements: [
              new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                  "ecr:GetAuthorizationToken",
                  "ecr:BatchCheckLayerAvailability",
                  "ecr:GetDownloadUrlForLayer",
                  "ecr:BatchGetImage"
                ],
                resources: ["*"]
              }),
              new PolicyStatement({
                effect: Effect.ALLOW,
                actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
                resources: [logGroup.logGroupArn]
              })
            ]
          })
        }
      }
    );

    // Create ECS cluster
    this.cluster = new Cluster(
      this,
      `${serviceNameAbbreviation}-MCPServerCluster`,
      {
        clusterName: `${props.projectName}-${serviceNameAbbreviation}-MCPCluster`,
        vpc: vpc,
        containerInsightsV2: props.prodLike
          ? ContainerInsights.ENABLED
          : ContainerInsights.ENHANCED
      }
    );

    // Create task definition
    const taskDefinition = new FargateTaskDefinition(
      this,
      `${serviceNameAbbreviation}-MCPServerTaskDefinition`,
      {
        memoryLimitMiB: mcpServerMemorySize,
        cpu: mcpServerCpu,
        taskRole: mcpServerTaskRole,
        executionRole: mcpServerExecutionRole
      }
    );

    // Build and add container to task definition using the ECS-specific image target
    const containerDefinition = taskDefinition.addContainer(
      `${serviceNameAbbreviation}-MCPServerContainer`,
      {
        image: ContainerImage.fromAsset(join(__dirname, "..", ".."), {
          file: "docker/Dockerfile.mcp",
          target: "mcp-server",
          buildArgs: {
            BUILDKIT_INLINE_CACHE: "true"
          },
          platform: Platform.LINUX_AMD64
        }),
        memoryLimitMiB: mcpServerMemorySize,
        logging: new AwsLogDriver({
          streamPrefix: "MCPServer",
          logGroup: logGroup,
          mode: AwsLogDriverMode.NON_BLOCKING
        }),
        environment: {
          WORKSPACE_BUCKET_NAME: this.workspaceBucket.bucketName,
          AWS_DEFAULT_REGION: this.region
        },
        healthCheck: {
          command: [
            `curl --fail http://localhost:${mcpServerPort}/health || exit 1`
          ],
          interval: Duration.seconds(30),
          retries: 3,
          timeout: Duration.seconds(10)
        }
      }
    );

    // Add port mapping
    containerDefinition.addPortMappings({
      containerPort: mcpServerPort,
      protocol: EcsProtocol.TCP
    });

    // Create ALB first with NetworkStack security group (following tile-server pattern)
    this.alb = new ApplicationLoadBalancer(
      this,
      `${serviceNameAbbreviation}-MCPServerApplicationLoadBalancer`,
      {
        vpc: vpc,
        vpcSubnets: {
          subnetType: SubnetType.PRIVATE_WITH_EGRESS
        },
        securityGroup: props.securityGroup,
        internetFacing: false
      }
    );

    // Create the Fargate service with pre-created ALB
    this.fargateService = new ApplicationLoadBalancedFargateService(
      this,
      `${serviceNameAbbreviation}-MCPServerService`,
      {
        cluster: this.cluster,
        taskDefinition: taskDefinition,
        serviceName: `${props.projectName}-${serviceNameAbbreviation}-MCPService`,
        desiredCount: 1,
        minHealthyPercent: 100,
        assignPublicIp: false,
        listenerPort: 80, // ALB listens on port 80, forwards to container `MCP_SERVER_PORT`
        publicLoadBalancer: false,
        taskSubnets: {
          subnetType: SubnetType.PRIVATE_WITH_EGRESS
        },
        loadBalancer: this.alb
      }
    );

    // Configure health check for the target group using health endpoint
    this.fargateService.targetGroup.configureHealthCheck({
      path: "/health",
      port: mcpServerPort.toString(),
      protocol: ElbProtocol.HTTP,
      healthyThresholdCount: 2,
      unhealthyThresholdCount: 3,
      timeout: Duration.seconds(10),
      interval: Duration.seconds(30)
    });

    // Add CDK-NAG suppressions
    if (nagSuppressions.length > 0) {
      NagSuppressions.addResourceSuppressions(this, nagSuppressions, true);
    }

    // Output ALB DNS name and workspace bucket
    this.exportValue(this.alb.loadBalancerDnsName, {
      name: `${serviceNameAbbreviation}-ALBDnsName`,
      description: "DNS name of the GeoAgent MCP Server ALB"
    });

    this.exportValue(this.workspaceBucket.bucketName, {
      name: `${serviceNameAbbreviation}-WorkspaceBucketName`,
      description: "Name of the GeoAgent S3 workspace bucket"
    });
  }
}
