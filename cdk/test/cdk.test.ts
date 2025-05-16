/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as chalk from 'chalk';
import { Annotations, Match } from 'aws-cdk-lib/assertions';
import { OSMLGeoAgentStack } from '../lib/osml-geo-agent-stack';
import { AwsSolutionsChecks, NagMessageLevel } from 'cdk-nag'
import { Aspects } from 'aws-cdk-lib';

interface NagFinding {
    resource: string;
    details: string;
    rule: string;
}

function generateNagReport(stack: cdk.Stack): void {
    const errors = Annotations.fromStack(stack).findError('*', Match.stringLikeRegexp('AwsSolutions-.*'));
    const warnings = Annotations.fromStack(stack).findWarning('*', Match.stringLikeRegexp('AwsSolutions-.*'));

    const formatFindings = (findings: any[], level: NagMessageLevel): NagFinding[] => {
        const regex = /(AwsSolutions-[A-Za-z0-9]+)\[([^\]]+)\]:\s*(.+)/;
        return findings.map(finding => {
            const match = finding.entry.data.match(regex);
            return {
                rule: match?.[1],
                resource: match?.[2],
                details: match?.[3],
            };
        });
    };

    const errorFindings = formatFindings(errors, NagMessageLevel.ERROR);
    const warningFindings = formatFindings(warnings, NagMessageLevel.WARN);

    // Generate the report
    const terminalWidth = process.stdout.columns || 80;
    process.stdout.write(chalk.black.bgWhite('\n================== CDK-NAG Compliance Report ==================\n'));
    process.stdout.write(`Stack: ${stack.stackName}\n`);
    process.stdout.write(`Generated: ${new Date().toISOString()}\n`);
    process.stdout.write(chalk.black.bgWhite('\n=============== Summary ===============\n'));
    process.stdout.write(`Total Errors: ${errorFindings.length}\n`);
    process.stdout.write(`Total Warnings: ${warningFindings.length}\n`);

    if (errorFindings.length > 0) {
        process.stdout.write(chalk.black.bgRed('\n=============== Errors ===============\n'));
        errorFindings.forEach((finding, index) => {
            process.stdout.write(`\n${finding.resource}\n`);
            process.stdout.write(`${finding.rule}\n`);
            process.stdout.write(`${finding.details}\n`);
        });
    }

    if (warningFindings.length > 0) {
        process.stdout.write(chalk.black.bgYellow('\n=============== Warnings ===============\n'));
        warningFindings.forEach((finding, index) => {
            process.stdout.write(`\n${finding.resource}\n`);
            process.stdout.write(`${finding.rule}\n`);
            process.stdout.write(`${finding.details}\n`);
        });
    }
    process.stdout.write('\n');
}


describe('cdk-nag Compliance Checks', () => {

    let app: cdk.App;
    let stack: OSMLGeoAgentStack;
    beforeAll(() => {
        app = new cdk.App({});

        const environment = {
            account: '123456789012', // Dummy account ID for testing
            region: 'us-west-2'      // Dummy region for testing
        };

        stack = new OSMLGeoAgentStack(app, 'OSMLGeoAgentsStack', {
            env: environment,
            targetVpcId: "vpc-xxxxx",
            workspaceBucketName: "fake-test-bucket",
        });

        // Add the cdk-nag AwsSolutions Pack with extra verbose logging enabled.
        Aspects.of(stack).add(new AwsSolutionsChecks({verbose: true}))

        generateNagReport(stack);
    });

    test('No unsuppressed Warnings', () => {
        const warnings = Annotations.fromStack(stack).findWarning(
            '*',
            Match.stringLikeRegexp('AwsSolutions-.*')
        );
        expect(warnings.length).toBe(0);
    });

    test('No unsuppressed Errors', () => {
        const errors = Annotations.fromStack(stack).findError(
            '*',
            Match.stringLikeRegexp('AwsSolutions-.*')
        );
        expect(errors.length).toBe(0);
    });
});
