/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { NagPackSuppression } from "cdk-nag";

export const nagSuppressions: NagPackSuppression[] = [
  {
    id: "AwsSolutions-IAM5",
    reason:
      "S3 workspace bucket requires wildcard access for STAC items, spatial operations, and other geospatial data management",
    appliesTo: ["Resource::arn:<AWS::Partition>:s3:::fake-test-bucket/*"]
  },
  {
    id: "AwsSolutions-IAM5",
    reason:
      "ECR GetAuthorizationToken requires wildcard resource access as per AWS service requirements",
    appliesTo: ["Resource::*"]
  },
  {
    id: "AwsSolutions-IAM5",
    reason:
      "EC2 ENI operations require wildcard access for VPC Lambda integration as per AWS service requirements",
    appliesTo: ["Action::ec2:*", "Resource::*"]
  },
  {
    id: "AwsSolutions-APIG2",
    reason: "Request validation is handled by the MCP server application"
  },
  {
    id: "AwsSolutions-COG4",
    reason: "JWT-based authorization is implemented via Lambda authorizer"
  },
  {
    id: "AwsSolutions-ECS2",
    reason:
      "Environment variables contain non-sensitive configuration data only"
  },
  {
    id: "AwsSolutions-ELB2",
    reason: "Access logging not required for internal load balancer"
  },
  {
    id: "AwsSolutions-ECS4",
    reason:
      "Container Insights are enabled (ENABLED for production, ENHANCED for non-production per code configuration)"
  },
  {
    id: "AwsSolutions-EC23",
    reason:
      "Security group allows VPC-scoped access only (Peer.ipv4(vpc.vpcCidrBlock)) for internal communication"
  },
  {
    id: "AwsSolutions-IAM4",
    reason:
      "API Gateway CloudWatch role automatically created by CDK when access logging is enabled - uses AWS managed policy for CloudWatch log operations",
    appliesTo: [
      "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
    ]
  }
];
