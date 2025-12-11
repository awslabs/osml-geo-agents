# Implementation Plan

- [x] 1. Remove authentication-related files and directories
  - Delete the Lambda authorizer code directory
  - Delete the OSMLAuthorizer construct file
  - Delete the OSMLAuth interface file
  - _Requirements: 11.1, 11.2, 11.3_

- [x] 2. Update stack-props.ts to remove authentication configuration
  - Remove OSMLAuth import statement
  - Remove auth property from OSMLGeoAgentStackProps interface
  - Remove apiStageName property from OSMLGeoAgentStackProps interface
  - Remove validateAuth function
  - Remove validateApiStageName function
  - Update validateProps function to remove calls to validateAuth and validateApiStageName
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.5_

- [x] 3. Update osml-geo-agent-stack.ts to remove authentication infrastructure
- [x] 3.1 Remove authentication-related imports
  - Remove API Gateway imports (AuthorizationType, ConnectionType, Cors, EndpointType, HttpIntegration, IdentitySource, LogGroupLogDestination, MethodLoggingLevel, RequestAuthorizer, RestApi, VpcLink)
  - Remove NetworkLoadBalancer import
  - Remove AlbListenerTarget import
  - Remove WAF imports (CfnWebACL, CfnWebACLAssociation)
  - Remove OSMLAuthorizer import
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 3.2 Remove public properties from OSMLGeoAgentStack class
  - Remove public nlb property declaration
  - Remove public restApi property declaration
  - Keep public alb, cluster, fargateService, and workspaceBucket properties
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 3.3 Remove authentication-related resource creation code
  - Remove API Gateway log group creation (apiGatewayLogGroup)
  - Remove Lambda authorizer log group creation (authorizerLogGroup)
  - Remove Lambda authorizer IAM role creation (authorizerLambdaRole)
  - Remove NLB creation and listener configuration
  - Remove VPC Link creation
  - Remove HTTP Integration creation
  - Remove OSMLAuthorizer construct instantiation
  - Remove RequestAuthorizer creation
  - Remove WAF Web ACL creation
  - Remove WAF Web ACL Association
  - Remove RestApi creation
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3.4 Fix ALB listener port configuration
  - Change listenerPort from mcpServerPort to 80 in ApplicationLoadBalancedFargateService configuration
  - Verify container port mapping remains at mcpServerPort (8080)
  - Verify security group allows port 80 for ALB listener and port 8080 for container
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 3.5 Update stack exports
  - Remove API Gateway URL export
  - Add ALB DNS name export
  - Keep workspace bucket name export
  - _Requirements: 1.7, 10.1, 10.2, 10.3_

- [x] 4. Update bin/app.ts to remove authentication properties
  - Remove auth property from geoAgentStack instantiation
  - Remove apiStageName property from geoAgentStack instantiation
  - _Requirements: 9.1, 9.2_

- [x] 5. Update nag-suppressions.ts to remove authentication-related suppressions
  - Remove AwsSolutions-APIG2 suppression (API Gateway request validation)
  - Remove AwsSolutions-COG4 suppression (JWT-based authorization)
  - Remove AwsSolutions-IAM4 suppression for API Gateway CloudWatch role
  - Remove AwsSolutions-IAM5 suppression for EC2 ENI operations (VPC Lambda)
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Update validation.test.ts to remove authentication tests
  - Remove auth property from validProps object
  - Remove entire "Auth Configuration Validation" test suite
  - Remove entire "API Stage Name Validation" test suite
  - _Requirements: 7.1, 7.2_

- [x] 7. Verify TypeScript compilation and CDK synthesis
  - Run npm run build to verify TypeScript compilation succeeds
  - Run npx cdk synth to verify CloudFormation template generation succeeds
  - _Requirements: 9.3, 11.4_

- [x] 8. Run unit tests to verify changes
  - Run npm run test to execute all CDK unit tests
  - Verify all remaining tests pass
  - Verify no tests depend on removed authentication infrastructure
  - _Requirements: 7.3, 7.4_

- [x] 9. Verify CloudFormation template structure
  - Synthesize the stack and inspect the CloudFormation template
  - Verify absence of API Gateway, NLB, Lambda authorizer, and WAF resources
  - Verify presence of ECS cluster, ALB, Fargate service, task definition, S3 bucket, IAM roles, and log groups
  - Verify ALB listener is configured for port 80
  - Verify exports include ALB DNS name and workspace bucket name, not API Gateway URL
  - _Requirements: 1.1, 1.2, 1.4, 1.6, 1.7, 2.1, 3.1, 3.3, 3.4, 3.5, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.1, 10.2, 10.3, 13.1_

- [x] 10. Update documentation to reflect architecture changes
  - Review cdk/README.md for references to API Gateway, authentication, or NLB
  - Update architecture diagrams or descriptions to show ALB as direct entry point
  - Remove any instructions related to authentication configuration
  - Update deployment instructions if they reference auth properties
  - Verify root README.md does not contain outdated authentication information
  - _Requirements: General documentation accuracy_

- [x] 11. Deploy and run integration tests
  - Deploy the modified CDK stack to a test environment
  - Run integration tests using the deployed TestStack Lambda
  - Verify MCP server responds to requests via ALB on port 80
  - Verify S3 workspace operations function correctly
  - Verify no authentication errors occur
  - _Requirements: 2.4, 8.8, 10.4_
