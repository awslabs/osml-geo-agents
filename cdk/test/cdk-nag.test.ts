/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import "source-map-support/register";

import { App, Aspects, Stack } from "aws-cdk-lib";
import { Annotations, Match } from "aws-cdk-lib/assertions";
import { SecurityGroup, Vpc } from "aws-cdk-lib/aws-ec2";
import { SynthesisMessage } from "aws-cdk-lib/cx-api";
import { AwsSolutionsChecks } from "cdk-nag";

import { OSMLGeoAgentStack } from "../lib/osml-geo-agent-stack";

interface NagFinding {
  resource: string;
  details: string;
  rule: string;
}

function generateNagReport(stack: Stack): void {
  const errors = Annotations.fromStack(stack).findError(
    "*",
    Match.stringLikeRegexp("AwsSolutions-.*")
  );
  const warnings = Annotations.fromStack(stack).findWarning(
    "*",
    Match.stringLikeRegexp("AwsSolutions-.*")
  );

  const formatFindings = (findings: SynthesisMessage[]): NagFinding[] => {
    const regex = /(AwsSolutions-[A-Za-z0-9]+)\[([^\]]+)]:\s*(.+)/;
    return findings.map((finding) => {
      const data =
        typeof finding.entry.data === "string"
          ? finding.entry.data
          : JSON.stringify(finding.entry.data);
      const match = data.match(regex);
      if (!match) {
        return {
          rule: "",
          resource: "",
          details: ""
        };
      }
      return {
        rule: match[1],
        resource: match[2],
        details: match[3]
      };
    });
  };

  const errorFindings = formatFindings(errors);
  const warningFindings = formatFindings(warnings);

  // Generate the report
  process.stdout.write(
    "\n================== CDK-NAG Compliance Report ==================\n"
  );
  process.stdout.write(`Stack: ${stack.stackName}\n`);
  process.stdout.write(`Generated: ${new Date().toISOString()}\n`);
  process.stdout.write("\n=============== Summary ===============\n");
  process.stdout.write(`Total Errors: ${errorFindings.length}\n`);
  process.stdout.write(`Total Warnings: ${warningFindings.length}\n`);

  if (errorFindings.length > 0) {
    process.stdout.write("\n=============== Errors ===============\n");
    errorFindings.forEach((finding) => {
      process.stdout.write(`\n${finding.resource}\n`);
      process.stdout.write(`${finding.rule}\n`);
      process.stdout.write(`${finding.details}\n`);
    });
  }

  if (warningFindings.length > 0) {
    process.stdout.write("\n=============== Warnings ===============\n");
    warningFindings.forEach((finding) => {
      process.stdout.write(`\n${finding.resource}\n`);
      process.stdout.write(`${finding.rule}\n`);
      process.stdout.write(`${finding.details}\n`);
    });
  }
  process.stdout.write("\n");
}

describe("cdk-nag Compliance Checks", () => {
  let app: App;
  let stack: OSMLGeoAgentStack;
  beforeAll(() => {
    app = new App({});

    const environment = {
      account: "123456789012", // Dummy account ID for testing
      region: "us-west-2" // Dummy region for testing
    };

    // Create test stack for resource lookup context
    const testStack = new Stack(app, "TestStack", { env: environment });

    // Create mock VPC and SecurityGroup for testing within stack context
    const mockVpc = Vpc.fromLookup(testStack, "TestVpc", {
      vpcId: "vpc-12345678"
    });

    const mockSecurityGroup = SecurityGroup.fromSecurityGroupId(
      testStack,
      "TestSecurityGroup",
      "sg-12345678"
    );

    stack = new OSMLGeoAgentStack(app, "OSMLGeoAgentsStack", {
      env: environment,
      projectName: "osml",
      prodLike: false,
      isAdc: false,
      vpc: mockVpc,
      securityGroup: mockSecurityGroup,
      workspaceBucketName: "fake-test-bucket"
    });

    // Add the cdk-nag AwsSolutions Pack with extra verbose logging enabled.
    Aspects.of(stack).add(
      new AwsSolutionsChecks({
        verbose: true
      })
    );

    generateNagReport(stack);
  });

  test("No unsuppressed Warnings", () => {
    const warnings = Annotations.fromStack(stack).findWarning(
      "*",
      Match.stringLikeRegexp("AwsSolutions-.*")
    );
    expect(warnings).toHaveLength(0);
  });

  test("No unsuppressed Errors", () => {
    const errors = Annotations.fromStack(stack).findError(
      "*",
      Match.stringLikeRegexp("AwsSolutions-.*")
    );
    expect(errors).toHaveLength(0);
  });
});
