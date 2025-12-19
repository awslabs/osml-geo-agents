/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

/**
 * @file Network construct for VPC and security group management.
 *
 * This construct provides networking infrastructure including:
 * - VPC creation or import
 * - Security group configuration
 * - Network isolation for GeoAgent MCP Server
 */

import { RemovalPolicy } from "aws-cdk-lib";
import {
  FlowLogDestination,
  FlowLogTrafficType,
  ISecurityGroup,
  IVpc,
  Peer,
  Port,
  SecurityGroup,
  SubnetFilter,
  SubnetSelection,
  SubnetType,
  Vpc
} from "aws-cdk-lib/aws-ec2";
import { LogGroup, RetentionDays } from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

import { BaseConfig, ConfigType, OSMLAccount } from "../types";

/**
 * Network configuration following UPPER_SNAKE_CASE convention to match osml-tile-server.
 */
export class NetworkConfig extends BaseConfig {
  /**
   * The name to assign to the created VPC.
   * @default "geo-agent-vpc"
   */
  public VPC_NAME?: string;

  /**
   * Existing VPC ID to import (optional).
   * If not provided, a new VPC will be created.
   */
  public VPC_ID?: string;

  /**
   * Define the maximum number of AZs for the VPC.
   */
  public MAX_AZS?: number;

  /**
   * Target subnets to use for resources (optional).
   * Required when VPC_ID is provided.
   */
  public TARGET_SUBNETS?: string[];

  /**
   * Security group ID to import (optional).
   * If not provided, a new security group will be created.
   */
  public SECURITY_GROUP_ID?: string;

  /**
   * The name to assign to the created security group.
   * @default "geo-agent-security-group"
   */
  public SECURITY_GROUP_NAME?: string;

  constructor(config: Partial<ConfigType> = {}) {
    super({
      VPC_NAME: "geo-agent-vpc",
      SECURITY_GROUP_NAME: "geo-agent-security-group",
      ...config
    });
  }
}

/**
 * Properties for the Network construct.
 */
export interface NetworkProps {
  /** The OSML account configuration. */
  readonly account: OSMLAccount;
  /** Optional network configuration. */
  readonly config?: NetworkConfig;
  /** Port for MCP server communication. */
  readonly mcpServerPort: number;
  /** Optional existing VPC to use directly. */
  readonly vpc?: IVpc;
}

/**
 * Network construct that manages VPC and security group resources.
 * Follows osml-tile-server pattern for consistency.
 */
export class Network extends Construct {
  /** The VPC for the network. */
  public readonly vpc: IVpc;

  /** The selected subnets based on configuration. */
  public readonly selectedSubnets: SubnetSelection;

  /** The security group for MCP server resources. */
  public readonly securityGroup: ISecurityGroup;

  /** Configuration options for Network. */
  public readonly config: NetworkConfig;

  /** The container port for security group rules. */
  private readonly containerPort: number;

  /**
   * Creates a new Network construct.
   *
   * @param scope - The scope in which to define this construct
   * @param id - The construct ID
   * @param props - The construct properties
   */
  constructor(scope: Construct, id: string, props: NetworkProps) {
    super(scope, id);

    // Check if a custom configuration was provided
    if (props.config instanceof NetworkConfig) {
      this.config = props.config;
    } else {
      // Create a new default configuration
      this.config = new NetworkConfig(
        (props.config as unknown as Partial<ConfigType>) ?? {}
      );
    }

    this.containerPort = props.mcpServerPort;

    // Resolve VPC - import existing or create new one
    this.vpc = this.resolveVpc(props);

    // Resolve security group - import existing or create new one
    this.securityGroup = this.resolveSecurityGroup();

    // Select subnets based on configuration
    this.selectedSubnets = this.resolveSubnets();
  }

  /**
   * Selects subnets within the VPC based on user specifications.
   * If target subnets are provided, those are selected; otherwise,
   * it defaults to selecting all private subnets with egress.
   *
   * @returns The selected subnet selection
   */
  private resolveSubnets(): SubnetSelection {
    // If specified subnets are provided, use them
    if (this.config.TARGET_SUBNETS) {
      return this.vpc.selectSubnets({
        subnetFilters: [SubnetFilter.byIds(this.config.TARGET_SUBNETS)]
      });
    } else {
      // Otherwise, select all private subnets
      return this.vpc.selectSubnets({
        subnetType: SubnetType.PRIVATE_WITH_EGRESS
      });
    }
  }

  /**
   * Resolves a VPC based on configuration.
   * If a VPC is provided directly, uses it.
   * If VPC_ID is provided, imports the existing VPC.
   * Otherwise, creates a new VPC with default settings.
   *
   * @param props - The network properties
   * @returns The VPC instance
   */
  private resolveVpc(props: NetworkProps): IVpc {
    if (props.vpc) {
      return props.vpc;
    }

    if (this.config.VPC_ID) {
      // Import existing VPC
      return Vpc.fromLookup(this, "ImportedVPC", {
        vpcId: this.config.VPC_ID,
        isDefault: false
      });
    } else {
      // Create new VPC
      const vpc = new Vpc(this, "VPC", {
        vpcName: this.config.VPC_NAME,
        maxAzs: this.config.MAX_AZS ?? 2,
        natGateways: 1,
        subnetConfiguration: [
          {
            cidrMask: 24,
            name: `${this.config.VPC_NAME}-Public`,
            subnetType: SubnetType.PUBLIC
          },
          {
            cidrMask: 24,
            name: `${this.config.VPC_NAME}-Private`,
            subnetType: SubnetType.PRIVATE_WITH_EGRESS
          }
        ]
      });

      // Add VPC flow logs for production environments
      if (props.account.prodLike) {
        const logGroup = new LogGroup(this, "VpcFlowLogGroup", {
          retention: RetentionDays.ONE_MONTH,
          removalPolicy: RemovalPolicy.RETAIN
        });

        vpc.addFlowLog("VpcFlowLog", {
          destination: FlowLogDestination.toCloudWatchLogs(logGroup),
          trafficType: FlowLogTrafficType.ALL
        });
      }

      return vpc;
    }
  }

  /**
   * Resolves a security group based on configuration.
   * If SECURITY_GROUP_ID is provided, imports the existing security group.
   * Otherwise, creates a new security group with default settings.
   *
   * @returns The security group instance
   */
  private resolveSecurityGroup(): ISecurityGroup {
    if (this.config.SECURITY_GROUP_ID) {
      // Import existing security group
      return SecurityGroup.fromSecurityGroupId(
        this,
        "ImportedSecurityGroup",
        this.config.SECURITY_GROUP_ID
      );
    } else {
      // Create new security group with outbound access
      const sg = new SecurityGroup(this, "SecurityGroup", {
        securityGroupName: this.config.SECURITY_GROUP_NAME,
        vpc: this.vpc,
        description: "Security group with outbound and MCP server access",
        allowAllOutbound: true
      });

      // Add ingress rule for ALB listener (port 80)
      sg.addIngressRule(
        Peer.ipv4(this.vpc.vpcCidrBlock),
        Port.tcp(80),
        "Allow inbound traffic to ALB on port 80"
      );

      // Add ingress rule for ALB to reach container
      sg.addIngressRule(
        Peer.ipv4(this.vpc.vpcCidrBlock),
        Port.tcp(this.containerPort),
        `Allow ALB to reach container on port ${this.containerPort}`
      );

      return sg;
    }
  }
}
