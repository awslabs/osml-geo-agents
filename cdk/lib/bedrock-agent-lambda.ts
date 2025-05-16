/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import * as cdk from 'aws-cdk-lib';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as fs from 'fs';
import * as path from 'path';
import {Construct} from 'constructs';

/**
 * Configuration for the Bedrock Agent. This is only needed if the choice is made to hardcode agent
 * settings in the CDK.
 */
export interface BedrockAgentConfiguration {
    /**
     * Action groups that define the agent's capabilities
     */
    readonly actionGroups: Array<cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty>;

    /**
     * Description of the agent
     */
    readonly description: string;

    /**
     * Instructions for the agent
     */
    readonly instruction: string;

    /**
     * Optional orchestration configuration overrides
     */
    readonly orchestrationConfig?: Record<string, any>;
}

/**
 *
 */
export interface BedrockAgentProps {
    /**
     * Optional alias for the agent
     * If provided, creates an alias pointing to the agent
     */
    readonly alias?: string;

    /**
     * The foundation model that will orchestrate the agent's actions
     */
    readonly foundationModel: bedrock.FoundationModelIdentifier;

    /**
     * The Lambda function that will handle agent actions
     */
    readonly handlerFunction: lambda.IFunction;

    /**
     * Optional idle session timeout in seconds
     * @default 1800 (30 minutes)
     */
    readonly idleSessionTtlInSeconds?: number;

    /**
     * Inline configuration for the agent
     * Either this or configPath must be provided
     */
    readonly configuration?: BedrockAgentConfiguration;

    /**
     * Path to the configuration directory
     * Either this or configuration must be provided
     */
    readonly configPath?: string;
}


/**
 * This is a generic L2 construct for a Bedrock Agent with tools implemented as a Lambda function.
 */
export class BedrockAgentLambda extends Construct {
    public readonly agent: cdk.aws_bedrock.CfnAgent;
    public readonly agentAlias?: cdk.aws_bedrock.CfnAgentAlias;

    /**
     * This function can be used to load an agent's configuration from files. Configuration items
     * like the definition of action groups or specialized prompt templates for an agent are logically
     * different from the infrastructure settings typically implemented in a CDK template. This provides
     * a means to separate that material from the CDK.
     *
     * @param { string } configPath - The root path to agent configuration files.
     * @private
     */
    private loadConfigurationFromPath(configPath: string): BedrockAgentConfiguration {
        try {
            // Read action groups
            const groupsPath = path.join(configPath, 'actionGroups', 'groups.json');
            if (!fs.existsSync(groupsPath)) {
                throw new Error(`Action groups file not found at ${groupsPath}`);
            }
            const actionGroups = JSON.parse(fs.readFileSync(groupsPath, 'utf8'));

            // Read description
            const descriptionPath = path.join(configPath, 'description.txt');
            if (!fs.existsSync(descriptionPath)) {
                throw new Error(`Description file not found at ${descriptionPath}`);
            }
            const description = fs.readFileSync(descriptionPath, 'utf8').trim();

            // Read instruction
            const instructionPath = path.join(configPath, 'instruction.txt');
            if (!fs.existsSync(instructionPath)) {
                throw new Error(`Instruction file not found at ${instructionPath}`);
            }
            const instruction = fs.readFileSync(instructionPath, 'utf8').trim();

            // Read optional orchestration config
            const overridesPath = path.join(configPath, 'overrides.json');
            const orchestrationConfig = fs.existsSync(overridesPath)
                ? JSON.parse(fs.readFileSync(overridesPath, 'utf8'))
                : undefined;

            return {
                actionGroups,
                description,
                instruction,
                orchestrationConfig,
            };
        } catch (error) {
            if (error instanceof Error) {
                throw new Error(`Failed to load configuration: ${error.message}`);
            }
            throw error;
        }
    }

    /**
     * Create an instance of a BedrockAgent
     *
     * @param { Construct } scope - The scope/stack in which to define this construct.
     * @param { string } id - The id of this construct within the current scope.
     * @param { BedrockAgentProps } props - The properties of this construct.
     */
    constructor(scope: Construct, id: string, props: BedrockAgentProps) {
        super(scope, id);

        // Validate that either configuration or configPath is provided
        if (!props.configuration && !props.configPath) {
            throw new Error('Either configuration or configPath must be provided');
        }
        if (props.configuration && props.configPath) {
            throw new Error('Only one of configuration or configPath should be provided');
        }

        // Get configuration either from props or load from path
        const config = props.configuration ?? this.loadConfigurationFromPath(props.configPath!);

        // Update action groups with executor
        const actionGroups = config.actionGroups.map(group => ({
            ...group,
            actionGroupExecutor: {
                lambda: props.handlerFunction.functionArn
            }
        }));

        // Create the IAM role for the Bedrock agent
        const agentRole = new iam.Role(this, 'AgentRole', {
            assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
            description: 'Role for Bedrock Agent',
        });

        agentRole.addToPolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['bedrock:InvokeModel'],
            resources: [
                `arn:aws:bedrock:${cdk.Stack.of(this).region}::foundation-model/${props.foundationModel.modelId}`,
            ]
        }));

        // Create the Bedrock agent using the configuration
        this.agent = new cdk.aws_bedrock.CfnAgent(this, 'Default', {
            agentName: `${id}-BedrockAgent`,
            agentResourceRoleArn: agentRole.roleArn,
            foundationModel: props.foundationModel.modelId,
            description: config.description,
            instruction: config.instruction,
            idleSessionTtlInSeconds: props.idleSessionTtlInSeconds ?? 1800,
            actionGroups,
            ...(config.orchestrationConfig && { orchestrationConfig: config.orchestrationConfig }),
        });

        // Create an alias if specified
        if (props.alias) {
            this.agentAlias = new cdk.aws_bedrock.CfnAgentAlias(this, 'Alias', {
                agentId: this.agent.attrAgentId,
                agentAliasName: props.alias
            });
        }

        // Add Lambda resource-based policy to allow Bedrock agent to invoke the function
        new lambda.CfnPermission(this, 'BedrockInvocationPermission', {
            action: 'lambda:InvokeFunction',
            functionName: props.handlerFunction.functionName,
            principal: 'bedrock.amazonaws.com',
            sourceArn: this.agent?.attrAgentArn,
        });
    }
}
