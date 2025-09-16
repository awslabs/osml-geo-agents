/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { join } from "path";

import { Stack, Duration, RemovalPolicy } from "aws-cdk-lib";
import {
  RestApi,
  HttpIntegration,
  EndpointType,
  Cors,
  AuthorizationType,
  IdentitySource,
  RequestAuthorizer,
  ConnectionType,
  VpcLink,
  AccessLogFormat,
  LogGroupLogDestination,
  MethodLoggingLevel
} from "aws-cdk-lib/aws-apigateway";
import { CfnWebACL, CfnWebACLAssociation } from "aws-cdk-lib/aws-wafv2";
import {
  SubnetType,
  Vpc,
  SecurityGroup,
  Peer,
  Port
} from "aws-cdk-lib/aws-ec2";
import {
  Cluster,
  ContainerInsights,
  FargateTaskDefinition,
  ContainerImage,
  AwsLogDriver,
  AwsLogDriverMode,
  Protocol as EcsProtocol
} from "aws-cdk-lib/aws-ecs";
import { ApplicationLoadBalancedFargateService } from "aws-cdk-lib/aws-ecs-patterns";
import {
  ApplicationLoadBalancer,
  NetworkLoadBalancer,
  Protocol as ElbProtocol
} from "aws-cdk-lib/aws-elasticloadbalancingv2";
import { AlbListenerTarget } from "aws-cdk-lib/aws-elasticloadbalancingv2-targets";
import {
  Role,
  PolicyStatement,
  Effect,
  ServicePrincipal,
  PolicyDocument
} from "aws-cdk-lib/aws-iam";
import { LogGroup, RetentionDays } from "aws-cdk-lib/aws-logs";
import { Bucket, BucketEncryption, IBucket } from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";
import { NagSuppressions } from "cdk-nag";

// Local OSML constructs
import { OSMLAuthorizer } from "./constructs/osml-authorizer";

import { validateProps, OSMLGeoAgentStackProps } from "./stack-props";
import { nagSuppressions } from "./nag-suppressions";

/**
 * CDK Stack that deploys the OSML Geo Agent MCP Server infrastructure.
 *
 * This stack creates a geospatial MCP (Model Context Protocol) server system that provides
 * geospatial analysis tools via API Gateway and ECS Fargate. The system includes:
 *
 * - An ECS Fargate service running the containerized MCP server
 * - An Application Load Balancer and Network Load Balancer for traffic routing
 * - An API Gateway REST API with VPC Link integration
 * - S3 bucket for workspace storage (created if not provided)
 * - Proper IAM permissions and VPC configuration
 *
 * The MCP server runs within a VPC using ECS Fargate for persistent connections
 * and uses S3 workspace storage for geospatial assets.
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
   * The Network Load Balancer for API Gateway integration.
   */
  public readonly nlb: NetworkLoadBalancer;

  /**
   * The API Gateway REST API.
   */
  public readonly restApi: RestApi;

  /**
   * The workspace S3 bucket.
   */
  public readonly workspaceBucket: IBucket;

  /**
   * Creates a new instance of the OSML Geo Agent Stack.
   *
   * This constructor sets up the complete infrastructure for the OSML Geo Agent MCP server,
   * including the ECS Fargate service, load balancers, API Gateway, S3 workspace, and proper networking and permissions.
   *
   * @param { Construct } scope - The construct scope in which to create the stack
   * @param { string } id - The unique identifier for this stack
   * @param { OSMLGeoAgentStackProps } props - Configuration properties including VPC ID and optional workspace bucket name
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
    const apiStageName = props.apiStageName || "prod";

    // The MCP server runs within a VPC
    const vpc = Vpc.fromLookup(this, "TargetVpc", {
      vpcId: props.targetVpcId
    });

    // Determine removal policy based on production flag
    const removalPolicy = props.isProd
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

    // Create log group for the Lambda authorizer function
    const authorizerLogGroup = new LogGroup(
      this,
      `${serviceNameAbbreviation}-AuthorizerLogGroup`,
      {
        logGroupName: `/aws/lambda/${props.projectName}-${serviceNameAbbreviation}-AuthorizerFunction`,
        retention: RetentionDays.TWO_WEEKS,
        removalPolicy: removalPolicy
      }
    );

    // Create log group for API Gateway access logs
    const apiGatewayLogGroup = new LogGroup(
      this,
      `${serviceNameAbbreviation}-APIGatewayLogGroup`,
      {
        logGroupName: `/aws/apigateway/${serviceNameAbbreviation}-MCP-RestApi`,
        retention: RetentionDays.TWO_WEEKS,
        removalPolicy: removalPolicy
      }
    );

    // Create IAM role for the Lambda authorizer function
    const authorizerLambdaRole = new Role(
      this,
      `${serviceNameAbbreviation}-AuthorizerLambdaRole`,
      {
        assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
        inlinePolicies: {
          LambdaVPCExecution: new PolicyDocument({
            statements: [
              new PolicyStatement({
                effect: Effect.ALLOW,
                actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
                resources: [authorizerLogGroup.logGroupArn]
              }),
              new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                  "ec2:CreateNetworkInterface",
                  "ec2:DescribeNetworkInterfaces",
                  "ec2:DeleteNetworkInterface"
                ],
                resources: ["*"]
              })
            ]
          })
        }
      }
    );

    // Create security group for the ECS service
    const mcpServerSecurityGroup = new SecurityGroup(
      this,
      `${serviceNameAbbreviation}-MCPServerSecurityGroup`,
      {
        vpc: vpc,
        description: "Security group for Geo Agent MCP Server ECS service",
        allowAllOutbound: true
      }
    );

    // Allow traffic on the container port
    mcpServerSecurityGroup.addIngressRule(
      Peer.ipv4(vpc.vpcCidrBlock),
      Port.tcp(mcpServerPort),
      "Allow traffic from VPC to MCP server"
    );

    // Create ECS cluster
    this.cluster = new Cluster(
      this,
      `${serviceNameAbbreviation}-MCPServerCluster`,
      {
        clusterName: `${props.projectName}-${serviceNameAbbreviation}-MCPCluster`,
        vpc: vpc,
        containerInsightsV2: props.isProd
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
          }
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

    // Create the Fargate service with Application Load Balancer
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
        listenerPort: mcpServerPort,
        publicLoadBalancer: false,
        taskSubnets: {
          subnetType: SubnetType.PRIVATE_WITH_EGRESS
        },
        securityGroups: [mcpServerSecurityGroup]
      }
    );

    // Get the ALB from the service
    this.alb = this.fargateService.loadBalancer;

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

    // Create Network Load Balancer for API Gateway integration
    this.nlb = new NetworkLoadBalancer(
      this,
      `${serviceNameAbbreviation}-MCPServerNLB`,
      {
        vpc: vpc,
        internetFacing: false,
        vpcSubnets: {
          subnetType: SubnetType.PRIVATE_WITH_EGRESS
        }
      }
    );

    // Add listener to NLB that forwards to ALB
    const nlbListener = this.nlb.addListener(
      `${serviceNameAbbreviation}-MCPServerNLBListener`,
      {
        port: 80,
        protocol: ElbProtocol.TCP
      }
    );

    nlbListener.addTargets(`${serviceNameAbbreviation}-MCPServerNLBTargets`, {
      targets: [new AlbListenerTarget(this.alb.listeners[0])],
      port: mcpServerPort
    });

    // Create VPC Link for API Gateway
    const vpcLink = new VpcLink(
      this,
      `${serviceNameAbbreviation}-MCPServerVpcLink`,
      {
        targets: [this.nlb]
      }
    );

    // Create HTTP integration for API Gateway - let proxy pass full path to Starlette
    const mcpServerIntegration = new HttpIntegration(
      `http://${this.nlb.loadBalancerDnsName}/{proxy}`,
      {
        httpMethod: "ANY",
        proxy: true,
        options: {
          vpcLink: vpcLink,
          connectionType: ConnectionType.VPC_LINK,
          requestParameters: {
            "integration.request.path.proxy": "method.request.path.proxy",
            "integration.request.header.Accept": "method.request.header.Accept",
            "integration.request.header.Host":
              "'${this.restApi.restApiId}.execute-api.${this.region}.${this.urlSuffix}'",
            "integration.request.header.X-Forwarded-Host": "context.domainName",
            "integration.request.header.X-Forwarded-Proto": "'https'",
            "integration.request.header.X-Forwarded-Path":
              "method.request.path.proxy"
          }
        }
      }
    );

    // Create OSML authorizer
    const authorizer = new OSMLAuthorizer(
      this,
      `${serviceNameAbbreviation}-MCPServerAuthorizer`,
      {
        auth: props.auth,
        name: `${serviceNameAbbreviation}-Authorizer`,
        vpc: vpc,
        vpcSubnets: {
          subnetType: SubnetType.PRIVATE_WITH_EGRESS
        },
        lambdaRole: authorizerLambdaRole
      }
    );

    // Create request authorizer
    const requestAuthorizer = new RequestAuthorizer(
      this,
      `${serviceNameAbbreviation}-MCPRequestAuthorizer`,
      {
        authorizerName: `${serviceNameAbbreviation}-Authorizer`,
        handler: authorizer.authorizerFunction,
        identitySources: [IdentitySource.header("Authorization")],
        resultsCacheTtl: Duration.minutes(0)
      }
    );

    // Create WAF Web ACL for API Gateway protection
    const webAcl = new CfnWebACL(this, "MCPServerWebACL", {
      scope: "REGIONAL",
      defaultAction: { allow: {} },
      rules: [
        {
          name: "AWSManagedRulesCommonRuleSet",
          priority: 1,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: "AWS",
              name: "AWSManagedRulesCommonRuleSet"
            }
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: "CommonRuleSetMetric"
          }
        },
        {
          name: "AWSManagedRulesKnownBadInputsRuleSet",
          priority: 2,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: "AWS",
              name: "AWSManagedRulesKnownBadInputsRuleSet"
            }
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: "KnownBadInputsMetric"
          }
        }
      ],
      visibilityConfig: {
        sampledRequestsEnabled: true,
        cloudWatchMetricsEnabled: true,
        metricName: `${serviceNameAbbreviation}-MCPServerWebACL`
      }
    });

    // Create the API Gateway REST API
    this.restApi = new RestApi(
      this,
      `${serviceNameAbbreviation}-MCPServerRestApi`,
      {
        restApiName: `${serviceNameAbbreviation}-MCP-RestApi`,
        description: "Geo Agent MCP Server",
        endpointTypes: [EndpointType.REGIONAL],
        deployOptions: {
          stageName: apiStageName,
          accessLogDestination: new LogGroupLogDestination(apiGatewayLogGroup),
          accessLogFormat: AccessLogFormat.jsonWithStandardFields({
            caller: true,
            httpMethod: true,
            ip: true,
            protocol: true,
            requestTime: true,
            resourcePath: true,
            responseLength: true,
            status: true,
            user: true
          }),
          // Add execution logging for all methods
          loggingLevel: MethodLoggingLevel.INFO,
          dataTraceEnabled: true,
          metricsEnabled: true
        },
        defaultIntegration: mcpServerIntegration,
        defaultMethodOptions: {
          authorizationType: AuthorizationType.CUSTOM,
          authorizer: requestAuthorizer,
          requestParameters: {
            "method.request.path.proxy": true,
            "method.request.header.Accept": true
          }
        },
        // Conditionally set CORS - only enable in non-production environments
        defaultCorsPreflightOptions: !props.isProd
          ? {
              allowOrigins: Cors.ALL_ORIGINS,
              allowHeaders: [
                "Content-Type",
                "X-Amz-Date",
                "Authorization",
                "X-Api-Key",
                "X-Amz-Security-Token",
                "X-Amz-User-Agent",
                "Accept",
                "mcp-session-id",
                "mcp-protocol-version"
              ],
              allowMethods: Cors.ALL_METHODS,
              allowCredentials: false
            }
          : undefined
      }
    );

    // Add proxy resource to handle all paths
    this.restApi.root.addProxy({
      defaultIntegration: mcpServerIntegration,
      anyMethod: true
    });

    // Associate WAF with API Gateway
    new CfnWebACLAssociation(
      this,
      `${serviceNameAbbreviation}-MCPServerWebACLAssociation`,
      {
        resourceArn: this.restApi.deploymentStage.stageArn,
        webAclArn: webAcl.attrArn
      }
    );

    // Add CDK-NAG suppressions
    if (nagSuppressions.length > 0) {
      NagSuppressions.addResourceSuppressions(this, nagSuppressions, true);
    }

    // Output MCP Server URL and workspace bucket
    this.exportValue(this.restApi.url, {
      name: `${serviceNameAbbreviation}-MCPRestApiUrl`,
      description: "URL of the GeoAgent MCP Server API Gateway"
    });

    this.exportValue(this.workspaceBucket.bucketName, {
      name: `${serviceNameAbbreviation}-WorkspaceBucketName`,
      description: "Name of the GeoAgent S3 workspace bucket"
    });
  }
}
