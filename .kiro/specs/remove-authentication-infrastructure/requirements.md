# Requirements Document

## Introduction

This document specifies the requirements for removing authentication infrastructure from the OSML Geo Agent CDK stack. The system currently deploys an API Gateway with Lambda-based JWT authentication, a Network Load Balancer for VPC Link integration, and associated WAF protection. The goal is to simplify the architecture by removing these components and making the Application Load Balancer (ALB) the direct entry point within a private VPC, eliminating public internet access and authentication layers.

## Glossary

- **ALB (Application Load Balancer)**: AWS load balancer that distributes HTTP/HTTPS traffic to ECS Fargate tasks
- **API Gateway**: AWS service that provides REST API endpoints with authentication and authorization
- **CDK (Cloud Development Kit)**: AWS infrastructure-as-code framework using TypeScript
- **ECS (Elastic Container Service)**: AWS container orchestration service running the MCP server
- **Lambda Authorizer**: AWS Lambda function that validates JWT tokens for API Gateway requests
- **MCP Server**: Model Context Protocol server providing geospatial analysis tools
- **NLB (Network Load Balancer)**: AWS load balancer that forwards TCP traffic to ALB for VPC Link integration
- **OSMLAuth**: TypeScript interface defining authentication configuration (authority and audience)
- **VPC (Virtual Private Cloud)**: Isolated network environment in AWS
- **VPC Link**: API Gateway integration that connects to private VPC resources via NLB
- **WAF (Web Application Firewall)**: AWS service protecting API Gateway from common web exploits

## Requirements

### Requirement 1

**User Story:** As a DevOps engineer, I want to remove the API Gateway infrastructure, so that the MCP server is only accessible within the private VPC without public internet exposure.

#### Acceptance Criteria

1. WHEN the CDK stack is deployed THEN the system SHALL NOT create an API Gateway REST API resource
2. WHEN the CDK stack is deployed THEN the system SHALL NOT create a VPC Link resource
3. WHEN the CDK stack is deployed THEN the system SHALL NOT create an HTTP Integration resource
4. WHEN the CDK stack is deployed THEN the system SHALL NOT create a WAF Web ACL resource
5. WHEN the CDK stack is deployed THEN the system SHALL NOT create a WAF Web ACL Association resource
6. WHEN the CDK stack is deployed THEN the system SHALL NOT create an API Gateway log group
7. WHEN the CDK stack is deployed THEN the system SHALL NOT export an API Gateway URL

### Requirement 2

**User Story:** As a DevOps engineer, I want to remove the Network Load Balancer, so that the infrastructure is simplified and the ALB serves as the direct entry point.

#### Acceptance Criteria

1. WHEN the CDK stack is deployed THEN the system SHALL NOT create a Network Load Balancer resource
2. WHEN the CDK stack is deployed THEN the system SHALL NOT create an NLB listener
3. WHEN the CDK stack is deployed THEN the system SHALL NOT create NLB target groups
4. WHEN the ALB is queried THEN the ALB SHALL remain operational and accessible within the VPC

### Requirement 3

**User Story:** As a DevOps engineer, I want to remove the Lambda authorizer infrastructure, so that no authentication validation occurs and the system relies on VPC network isolation for security.

#### Acceptance Criteria

1. WHEN the CDK stack is deployed THEN the system SHALL NOT create an OSMLAuthorizer construct
2. WHEN the CDK stack is deployed THEN the system SHALL NOT create a RequestAuthorizer resource
3. WHEN the CDK stack is deployed THEN the system SHALL NOT create a Lambda authorizer IAM role
4. WHEN the CDK stack is deployed THEN the system SHALL NOT create a Lambda authorizer log group
5. WHEN the CDK stack is deployed THEN the system SHALL NOT create a Lambda authorizer function

### Requirement 4

**User Story:** As a developer, I want to remove authentication-related configuration properties, so that the stack props interface reflects the simplified architecture without authentication requirements.

#### Acceptance Criteria

1. WHEN the OSMLGeoAgentStackProps interface is defined THEN the interface SHALL NOT include an auth property
2. WHEN the OSMLGeoAgentStackProps interface is defined THEN the interface SHALL NOT include an apiStageName property
3. WHEN the validateProps function is called THEN the function SHALL NOT validate auth configuration
4. WHEN the validateProps function is called THEN the function SHALL NOT validate apiStageName configuration
5. WHEN the stack props are validated THEN the validation SHALL succeed without requiring auth or apiStageName properties

### Requirement 5

**User Story:** As a developer, I want to remove authentication-related imports and dependencies, so that the codebase is clean and does not reference unused authentication components.

#### Acceptance Criteria

1. WHEN the osml-geo-agent-stack.ts file is compiled THEN the file SHALL NOT import API Gateway-related classes
2. WHEN the osml-geo-agent-stack.ts file is compiled THEN the file SHALL NOT import NetworkLoadBalancer class
3. WHEN the osml-geo-agent-stack.ts file is compiled THEN the file SHALL NOT import WAF-related classes
4. WHEN the osml-geo-agent-stack.ts file is compiled THEN the file SHALL NOT import OSMLAuthorizer construct
5. WHEN the stack-props.ts file is compiled THEN the file SHALL NOT import OSMLAuth interface

### Requirement 6

**User Story:** As a developer, I want to remove authentication-related CDK Nag suppressions, so that the compliance checks reflect the actual infrastructure without unnecessary suppressions.

#### Acceptance Criteria

1. WHEN the nag-suppressions.ts file is defined THEN the file SHALL NOT include AwsSolutions-APIG2 suppression
2. WHEN the nag-suppressions.ts file is defined THEN the file SHALL NOT include AwsSolutions-COG4 suppression
3. WHEN the nag-suppressions.ts file is defined THEN the file SHALL NOT include AwsSolutions-IAM4 suppression for API Gateway
4. WHEN the nag-suppressions.ts file is defined THEN the file SHALL NOT include AwsSolutions-IAM5 suppression for EC2 ENI operations

### Requirement 7

**User Story:** As a developer, I want to remove authentication-related test cases, so that the test suite validates only the components that exist in the simplified architecture.

#### Acceptance Criteria

1. WHEN the validation.test.ts file is executed THEN the file SHALL NOT include auth configuration validation tests
2. WHEN the validation.test.ts file is executed THEN the file SHALL NOT include API stage name validation tests
3. WHEN the validation.test.ts file is executed THEN the test suite SHALL pass without requiring auth or apiStageName in validProps
4. WHEN the validation.test.ts file is executed THEN all remaining tests SHALL continue to pass

### Requirement 8

**User Story:** As a DevOps engineer, I want to preserve the ECS and ALB infrastructure, so that the MCP server continues to run and serve requests within the private VPC.

#### Acceptance Criteria

1. WHEN the CDK stack is deployed THEN the system SHALL create an ECS cluster
2. WHEN the CDK stack is deployed THEN the system SHALL create an Application Load Balancer
3. WHEN the CDK stack is deployed THEN the system SHALL create a Fargate service
4. WHEN the CDK stack is deployed THEN the system SHALL create a task definition with container
5. WHEN the CDK stack is deployed THEN the system SHALL create S3 workspace bucket
6. WHEN the CDK stack is deployed THEN the system SHALL create ECS task and execution IAM roles
7. WHEN the CDK stack is deployed THEN the system SHALL create container log group
8. WHEN the ALB DNS name is accessed from within the VPC THEN the MCP server SHALL respond to health check requests

### Requirement 9

**User Story:** As a DevOps engineer, I want to update the CDK app entry point, so that it does not pass authentication-related properties to the stack.

#### Acceptance Criteria

1. WHEN the bin/app.ts file instantiates OSMLGeoAgentStack THEN the instantiation SHALL NOT include an auth property
2. WHEN the bin/app.ts file instantiates OSMLGeoAgentStack THEN the instantiation SHALL NOT include an apiStageName property
3. WHEN the CDK app is synthesized THEN the synthesis SHALL succeed without authentication configuration

### Requirement 10

**User Story:** As a DevOps engineer, I want to update stack exports, so that only the ALB DNS name and workspace bucket are exported, not the API Gateway URL.

#### Acceptance Criteria

1. WHEN the CDK stack is deployed THEN the stack SHALL export the ALB DNS name
2. WHEN the CDK stack is deployed THEN the stack SHALL export the workspace bucket name
3. WHEN the CDK stack is deployed THEN the stack SHALL NOT export an API Gateway URL
4. WHEN the TestStack references the ALB DNS name THEN the reference SHALL resolve correctly

### Requirement 11

**User Story:** As a developer, I want to delete authentication-related source files, so that the codebase does not contain unused code.

#### Acceptance Criteria

1. WHEN the codebase is reviewed THEN the cdk/lambda/authorizer/ directory SHALL NOT exist
2. WHEN the codebase is reviewed THEN the cdk/lib/constructs/osml-authorizer.ts file SHALL NOT exist
3. WHEN the codebase is reviewed THEN the cdk/lib/constructs/osml-auth.ts file SHALL NOT exist
4. WHEN the CDK stack is compiled THEN the compilation SHALL succeed without these files

### Requirement 12

**User Story:** As a developer, I want to update the OSMLGeoAgentStack class, so that it does not expose authentication-related public properties.

#### Acceptance Criteria

1. WHEN the OSMLGeoAgentStack class is defined THEN the class SHALL NOT include a public nlb property
2. WHEN the OSMLGeoAgentStack class is defined THEN the class SHALL NOT include a public restApi property
3. WHEN the OSMLGeoAgentStack class is defined THEN the class SHALL include a public alb property
4. WHEN the OSMLGeoAgentStack class is defined THEN the class SHALL include a public cluster property
5. WHEN the OSMLGeoAgentStack class is defined THEN the class SHALL include a public fargateService property
6. WHEN the OSMLGeoAgentStack class is defined THEN the class SHALL include a public workspaceBucket property

### Requirement 13

**User Story:** As a DevOps engineer, I want the ALB to listen on standard HTTP port 80, so that integration tests and internal clients can connect using the standard port.

#### Acceptance Criteria

1. WHEN the Fargate service is created THEN the ALB listener SHALL be configured to listen on port 80
2. WHEN the container is created THEN the container SHALL expose port 8080 (mcpServerPort)
3. WHEN the ALB receives a request on port 80 THEN the ALB SHALL forward the request to the container on port 8080
4. WHEN the security group is configured THEN the security group SHALL allow ingress on port 80 for the ALB listener
5. WHEN the security group is configured THEN the security group SHALL allow ingress on port 8080 for ALB to container communication
