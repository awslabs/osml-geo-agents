# Design Document

## Overview

This design document outlines the approach for removing authentication infrastructure from the OSML Geo Agent CDK stack. The current architecture includes API Gateway with Lambda-based JWT authentication, a Network Load Balancer for VPC Link integration, and WAF protection. The simplified architecture will eliminate these components, making the Application Load Balancer (ALB) the direct entry point within a private VPC.

The removal process involves modifying TypeScript CDK code, deleting authentication-related files, updating configuration interfaces, and adjusting test suites. The core ECS Fargate service, ALB, and S3 workspace infrastructure will remain unchanged.

## Architecture

### Current Architecture

```
Internet → API Gateway (with JWT auth) → VPC Link → NLB → ALB → ECS Fargate (MCP Server)
                ↓
         Lambda Authorizer
         (JWT validation)
```

### Target Architecture

```
Private VPC → ALB → ECS Fargate (MCP Server)
```

### Key Changes

1. **Remove Public Internet Access**: Eliminate API Gateway as the public-facing endpoint
2. **Remove Authentication Layer**: Delete Lambda authorizer and JWT validation
3. **Simplify Load Balancing**: Remove NLB (only needed for VPC Link), keep ALB as direct entry point
4. **Rely on VPC Isolation**: Security through network isolation instead of application-level authentication

## Components and Interfaces

### Files to Modify

#### 1. cdk/lib/osml-geo-agent-stack.ts

**Changes:**
- Remove imports: API Gateway classes, NetworkLoadBalancer, WAF classes, OSMLAuthorizer
- Remove public properties: `nlb`, `restApi`
- Remove code sections:
  - API Gateway log group creation
  - Lambda authorizer log group creation
  - Lambda authorizer IAM role creation
  - NLB creation and listener configuration
  - VPC Link creation
  - HTTP Integration creation
  - OSMLAuthorizer construct instantiation
  - RequestAuthorizer creation
  - WAF Web ACL creation
  - WAF Web ACL Association
  - RestApi creation
  - API Gateway URL export
- Fix ALB listener port:
  - Change `listenerPort: mcpServerPort` to `listenerPort: 80`
  - This ensures the ALB listens on standard HTTP port 80
  - The `mcpServerPort` (8080) should only be used for the container port mapping
  - Security group already correctly allows both port 80 (ALB listener) and port 8080 (container)
- Keep intact:
  - ECS cluster creation
  - Task definition and container configuration
  - ALB creation
  - Fargate service creation
  - S3 workspace bucket
  - IAM roles for ECS tasks
  - Container log group
- Add: ALB DNS name export

**Interface Changes:**
```typescript
// Remove these public properties
public readonly nlb: NetworkLoadBalancer;
public readonly restApi: RestApi;

// Keep these public properties
public readonly cluster: Cluster;
public readonly fargateService: ApplicationLoadBalancedFargateService;
public readonly alb: ApplicationLoadBalancer;
public readonly workspaceBucket: IBucket;
```

#### 2. cdk/lib/stack-props.ts

**Changes:**
- Remove `auth: OSMLAuth` property from OSMLGeoAgentStackProps interface
- Remove `apiStageName?: string` property from OSMLGeoAgentStackProps interface
- Remove `OSMLAuth` import
- Remove `validateAuth()` function
- Remove `validateApiStageName()` function
- Update `validateProps()` to remove calls to `validateAuth()` and `validateApiStageName()`

**Interface Changes:**
```typescript
// Before
export interface OSMLGeoAgentStackProps extends StackProps {
  // ... other properties
  apiStageName?: string;
  auth: OSMLAuth;
}

// After
export interface OSMLGeoAgentStackProps extends StackProps {
  // ... other properties (no auth or apiStageName)
}
```

#### 3. cdk/bin/app.ts

**Changes:**
- Remove `auth: deployment.auth` from geoAgentStack instantiation
- Remove `apiStageName: deployment.geoAgentConfig?.API_STAGE_NAME` from geoAgentStack instantiation

**Code Changes:**
```typescript
// Before
const geoAgentStack = new OSMLGeoAgentStack(app, `${deployment.projectName}-GeoAgent`, {
  // ... other props
  apiStageName: deployment.geoAgentConfig?.API_STAGE_NAME,
  auth: deployment.auth,
});

// After
const geoAgentStack = new OSMLGeoAgentStack(app, `${deployment.projectName}-GeoAgent`, {
  // ... other props (no auth or apiStageName)
});
```

#### 4. cdk/lib/nag-suppressions.ts

**Changes:**
- Remove suppression for `AwsSolutions-APIG2` (API Gateway request validation)
- Remove suppression for `AwsSolutions-COG4` (JWT-based authorization)
- Remove suppression for `AwsSolutions-IAM4` (API Gateway CloudWatch role)
- Remove suppression for `AwsSolutions-IAM5` with `Action::ec2:*` (VPC Lambda ENI operations)

#### 5. cdk/test/validation.test.ts

**Changes:**
- Remove `auth` property from `validProps` object
- Remove entire "Auth Configuration Validation" test suite
- Remove entire "API Stage Name Validation" test suite
- Update remaining tests to work without auth property

### Files to Delete

1. **cdk/lambda/authorizer/** - Entire directory containing Lambda authorizer code
   - `lambda_function.py` - JWT validation logic

2. **cdk/lib/constructs/osml-authorizer.ts** - OSMLAuthorizer construct definition

3. **cdk/lib/constructs/osml-auth.ts** - OSMLAuth interface definition

### Files to Keep Unchanged

- **cdk/lib/network-stack.ts** - VPC and security group configuration
- **cdk/lib/test-stack.ts** - Integration test infrastructure (uses ALB DNS directly)
- All files in **cdk/lib/constructs/geo-agent/** - Network constructs
- All files in **cdk/lib/constructs/test/** - Test constructs

## Data Models

### Stack Props Interface

**Before:**
```typescript
export interface OSMLGeoAgentStackProps extends StackProps {
  projectName: string;
  prodLike: boolean;
  isAdc: boolean;
  serviceNameAbbreviation?: string;
  vpc: IVpc;
  securityGroup: ISecurityGroup;
  workspaceBucketName?: string;
  mcpServerCpu?: number;
  mcpServerMemorySize?: number;
  mcpServerPort?: number;
  apiStageName?: string;  // REMOVE
  auth: OSMLAuth;         // REMOVE
}
```

**After:**
```typescript
export interface OSMLGeoAgentStackProps extends StackProps {
  projectName: string;
  prodLike: boolean;
  isAdc: boolean;
  serviceNameAbbreviation?: string;
  vpc: IVpc;
  securityGroup: ISecurityGroup;
  workspaceBucketName?: string;
  mcpServerCpu?: number;
  mcpServerMemorySize?: number;
  mcpServerPort?: number;
  // auth and apiStageName removed
}
```

### Stack Exports

**Before:**
```typescript
// Export API Gateway URL
this.exportValue(this.restApi.url, {
  name: `${serviceNameAbbreviation}-MCPRestApiUrl`,
  description: "URL of the GeoAgent MCP Server API Gateway"
});

// Export workspace bucket
this.exportValue(this.workspaceBucket.bucketName, {
  name: `${serviceNameAbbreviation}-WorkspaceBucketName`,
  description: "Name of the GeoAgent S3 workspace bucket"
});
```

**After:**
```typescript
// Export ALB DNS name
this.exportValue(this.alb.loadBalancerDnsName, {
  name: `${serviceNameAbbreviation}-ALBDnsName`,
  description: "DNS name of the GeoAgent MCP Server ALB"
});

// Export workspace bucket
this.exportValue(this.workspaceBucket.bucketName, {
  name: `${serviceNameAbbreviation}-WorkspaceBucketName`,
  description: "Name of the GeoAgent S3 workspace bucket"
});
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, most of the acceptance criteria are specific examples that verify the absence or presence of particular resources in the CloudFormation template or code structure. These are best validated through example-based tests rather than property-based tests, as they check for specific conditions rather than universal properties across a range of inputs.

### Example 1: CloudFormation Template Resource Absence

*For the* synthesized CloudFormation template, the template should not contain any API Gateway REST API resources (AWS::ApiGateway::RestApi).

**Validates: Requirements 1.1**

### Example 2: CloudFormation Template Resource Absence

*For the* synthesized CloudFormation template, the template should not contain any VPC Link resources (AWS::ApiGateway::VpcLink).

**Validates: Requirements 1.2**

### Example 3: CloudFormation Template Resource Absence

*For the* synthesized CloudFormation template, the template should not contain any WAF Web ACL resources (AWS::WAFv2::WebACL).

**Validates: Requirements 1.4**

### Example 4: CloudFormation Template Resource Absence

*For the* synthesized CloudFormation template, the template should not contain any log groups with the API Gateway naming pattern (/aws/apigateway/).

**Validates: Requirements 1.6**

### Example 5: CloudFormation Template Export Absence

*For the* synthesized CloudFormation template, the template should not contain any exports with the API Gateway URL naming pattern (MCPRestApiUrl).

**Validates: Requirements 1.7, 10.3**

### Example 6: CloudFormation Template Resource Absence

*For the* synthesized CloudFormation template, the template should not contain any Network Load Balancer resources (AWS::ElasticLoadBalancingV2::LoadBalancer with Type: network).

**Validates: Requirements 2.1**

### Example 7: CloudFormation Template Resource Absence

*For the* synthesized CloudFormation template, the template should not contain any Lambda functions with the authorizer naming pattern.

**Validates: Requirements 3.1, 3.5**

### Example 8: CloudFormation Template Resource Absence

*For the* synthesized CloudFormation template, the template should not contain any IAM roles with the authorizer naming pattern.

**Validates: Requirements 3.3**

### Example 9: CloudFormation Template Resource Absence

*For the* synthesized CloudFormation template, the template should not contain any log groups with the authorizer naming pattern (/aws/lambda/*Authorizer*).

**Validates: Requirements 3.4**

### Example 10: TypeScript Interface Definition

*For the* OSMLGeoAgentStackProps interface, the interface should not include an auth property or apiStageName property.

**Validates: Requirements 4.1, 4.2**

### Example 11: Validation Function Behavior

*For the* validateProps function, calling it with valid props that lack auth and apiStageName properties should succeed without throwing an error.

**Validates: Requirements 4.3, 4.4, 4.5**

### Example 12: Import Statement Absence

*For the* osml-geo-agent-stack.ts file, the file should not import any API Gateway-related classes, NetworkLoadBalancer, WAF-related classes, or OSMLAuthorizer.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

### Example 13: Import Statement Absence

*For the* stack-props.ts file, the file should not import the OSMLAuth interface.

**Validates: Requirements 5.5**

### Example 14: CDK Nag Suppressions Absence

*For the* nag-suppressions.ts file, the suppressions array should not contain entries for AwsSolutions-APIG2, AwsSolutions-COG4, AwsSolutions-IAM4 (API Gateway), or AwsSolutions-IAM5 (EC2 ENI operations).

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Example 15: Test Suite Structure

*For the* validation.test.ts file, the file should not contain test suites for "Auth Configuration Validation" or "API Stage Name Validation".

**Validates: Requirements 7.1, 7.2**

### Example 16: Test Suite Execution

*For the* validation.test.ts file, running the test suite should result in all tests passing.

**Validates: Requirements 7.3, 7.4**

### Example 17: CloudFormation Template Resource Presence

*For the* synthesized CloudFormation template, the template should contain an ECS cluster (AWS::ECS::Cluster), Application Load Balancer (AWS::ElasticLoadBalancingV2::LoadBalancer with Type: application), Fargate service (AWS::ECS::Service), task definition (AWS::ECS::TaskDefinition), S3 bucket or bucket reference, ECS IAM roles, and container log group.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7**

### Example 18: CDK App Instantiation

*For the* bin/app.ts file, the OSMLGeoAgentStack instantiation should not include auth or apiStageName properties.

**Validates: Requirements 9.1, 9.2**

### Example 19: CDK Synthesis

*For the* CDK application, running cdk synth should complete successfully without errors.

**Validates: Requirements 9.3**

### Example 20: CloudFormation Template Exports

*For the* synthesized CloudFormation template, the template should export the ALB DNS name and workspace bucket name.

**Validates: Requirements 10.1, 10.2**

### Example 21: TestStack Reference

*For the* TestStack, the stack should correctly reference the ALB DNS name from the OSMLGeoAgentStack.

**Validates: Requirements 10.4**

### Example 22: File System Structure

*For the* codebase, the cdk/lambda/authorizer/ directory, cdk/lib/constructs/osml-authorizer.ts file, and cdk/lib/constructs/osml-auth.ts file should not exist.

**Validates: Requirements 11.1, 11.2, 11.3**

### Example 23: TypeScript Compilation

*For the* CDK project, running npm run build should complete successfully without errors.

**Validates: Requirements 11.4**

### Example 24: Class Property Definitions

*For the* OSMLGeoAgentStack class, the class should not include public nlb or restApi properties, and should include public alb, cluster, fargateService, and workspaceBucket properties.

**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6**

### Example 25: ALB Listener Port Configuration

*For the* ApplicationLoadBalancedFargateService configuration, the listenerPort should be set to 80 (standard HTTP port), not mcpServerPort (8080).

**Validates: Requirements 13.1**

### Example 26: Container Port Configuration

*For the* container definition, the container port mapping should be set to mcpServerPort (8080), and the ALB should forward traffic from port 80 to port 8080.

**Validates: Requirements 13.2, 13.3**

### Example 27: Security Group Configuration

*For the* security group, ingress rules should allow port 80 for the ALB listener and port 8080 for ALB to container communication.

**Validates: Requirements 13.4, 13.5**

## Error Handling

### Compilation Errors

If TypeScript compilation fails after removing authentication components:
1. Check for remaining references to removed imports (API Gateway, OSMLAuthorizer, etc.)
2. Verify all removed properties are not accessed elsewhere in the code
3. Check for circular dependencies or missing imports

### Validation Errors

If prop validation fails:
1. Ensure validateProps no longer calls validateAuth or validateApiStageName
2. Verify the OSMLGeoAgentStackProps interface does not require auth or apiStageName
3. Check that all callers of validateProps do not pass these properties

### Test Failures

If tests fail after modifications:
1. Verify validProps in test files does not include auth or apiStageName
2. Check that removed test suites are completely deleted, not just commented out
3. Ensure remaining tests do not depend on authentication infrastructure

### CDK Synthesis Errors

If cdk synth fails:
1. Verify all removed resources are not referenced in the stack constructor
2. Check that exports reference valid resources (ALB instead of API Gateway)
3. Ensure TestStack references are updated to use ALB DNS name

## Testing Strategy

### Unit Testing Approach

The testing strategy focuses on example-based tests that verify specific conditions in the code and CloudFormation templates. Since this is a refactoring task that removes infrastructure components, the tests primarily check for the absence of specific resources and the presence of required resources.

**Test Categories:**

1. **CloudFormation Template Tests**: Synthesize the stack and verify the template structure
   - Check for absence of API Gateway, NLB, Lambda authorizer, WAF resources
   - Check for presence of ECS, ALB, S3, IAM resources
   - Verify exports contain ALB DNS name and bucket name, not API Gateway URL

2. **TypeScript Interface Tests**: Verify interface definitions
   - Check OSMLGeoAgentStackProps does not include auth or apiStageName
   - Verify class properties match expected structure

3. **Validation Function Tests**: Test prop validation behavior
   - Verify validateProps succeeds without auth or apiStageName
   - Ensure validation errors are thrown for other invalid inputs

4. **Code Structure Tests**: Verify file and import structure
   - Check for absence of deleted files
   - Verify import statements do not reference removed components
   - Check CDK Nag suppressions array

5. **Compilation Tests**: Verify the project builds successfully
   - Run npm run build and verify success
   - Run cdk synth and verify success

6. **Existing Test Suite**: Run existing validation tests
   - Verify all remaining tests pass
   - Ensure no tests depend on removed authentication infrastructure

### Test Framework

- **Jest**: Primary test framework for CDK unit tests
- **CDK Assertions**: Use `Template.fromStack()` to verify CloudFormation template structure
- **TypeScript Compiler**: Verify compilation succeeds

### Test Execution

```bash
# Run all CDK tests
cd cdk
npm run test

# Run specific test file
npm run test -- validation.test.ts

# Build and synthesize
npm run build
npx cdk synth
```

### Integration Testing

After deploying the modified stack, integration tests should verify the MCP server is accessible via the ALB within the VPC:

1. **Deploy the Stack**: Deploy the modified CDK stack to a test environment
2. **Run Integration Tests**: Execute the TestStack integration tests that connect to the ALB
3. **Verify MCP Server**: Confirm the MCP server responds to requests via the ALB DNS name
4. **Test Workspace Operations**: Verify S3 workspace operations function correctly

**Integration Test Execution:**

```bash
# Deploy the stack (includes TestStack with integration test Lambda)
cd cdk
npx cdk deploy --all

# Run integration tests using the deployed Lambda
cd ..
./scripts/run-integration-tests.sh
```

**Integration Test Validation:**
- MCP server health endpoint responds successfully via ALB
- Geospatial tools are accessible and functional
- S3 workspace operations (load, list, unload) work correctly
- No authentication errors occur (since auth is removed)
- TestStack Lambda can successfully connect to the ALB

### Coverage Goals

- All modified files should have tests verifying the changes
- CloudFormation template should be validated for both absence and presence of resources
- Compilation and synthesis should be verified as part of the test suite
- Integration tests should verify the deployed infrastructure functions correctly without authentication
