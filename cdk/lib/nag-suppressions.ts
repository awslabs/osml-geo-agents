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
  }
];
