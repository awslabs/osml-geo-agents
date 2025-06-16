/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { aws_bedrock, Stack } from "aws-cdk-lib";
import { FoundationModelIdentifier } from "aws-cdk-lib/aws-bedrock";
import {
  Effect,
  PolicyStatement,
  Role,
  ServicePrincipal
} from "aws-cdk-lib/aws-iam";
import { CfnPermission, IFunction } from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";

/**
 * Configuration for the Bedrock Agent. This is only needed if the choice is made to hardcode agent
 * settings in the CDK.
 */
export interface BedrockAgentConfiguration {
  /**
   * Action groups that define the agent's capabilities
   */
  readonly actionGroups: Array<aws_bedrock.CfnAgent.AgentActionGroupProperty>;

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
  readonly orchestrationConfig?: Record<string, unknown>;
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
  readonly foundationModel: FoundationModelIdentifier;

  /**
   * The Lambda function that will handle agent actions
   */
  readonly handlerFunction: IFunction;

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
  public readonly agent: aws_bedrock.CfnAgent;
  public readonly agentAlias?: aws_bedrock.CfnAgentAlias;

  /**
   * This function can be used to load an agent's configuration from files. Configuration items
   * like the definition of action groups or specialized prompt templates for an agent are logically
   * different from the infrastructure settings typically implemented in a CDK template. This provides
   * a means to separate that material from the CDK.
   *
   * @param { string } configPath - The root path to agent configuration files.
   * @private
   */
  private loadConfigurationFromPath(
    configPath: string
  ): BedrockAgentConfiguration {
    try {
      // Read action groups
      const groupsPath = join(configPath, "actionGroups", "groups.json");
      if (!existsSync(groupsPath)) {
        throw new Error(`Action groups file not found at ${groupsPath}`);
      }
      const actionGroups = JSON.parse(
        readFileSync(groupsPath, "utf8")
      ) as Array<aws_bedrock.CfnAgent.AgentActionGroupProperty>;

      // Read description
      const descriptionPath = join(configPath, "description.txt");
      if (!existsSync(descriptionPath)) {
        throw new Error(`Description file not found at ${descriptionPath}`);
      }
      const description = readFileSync(descriptionPath, "utf8").trim();

      // Read instruction
      const instructionPath = join(configPath, "instruction.txt");
      if (!existsSync(instructionPath)) {
        throw new Error(`Instruction file not found at ${instructionPath}`);
      }
      const instruction = readFileSync(instructionPath, "utf8").trim();

      // Read optional orchestration config
      const overridesPath = join(configPath, "overrides.json");
      const orchestrationConfig = existsSync(overridesPath)
        ? (JSON.parse(readFileSync(overridesPath, "utf8")) as Record<
            string,
            unknown
          >)
        : undefined;

      return {
        actionGroups,
        description,
        instruction,
        orchestrationConfig
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
      throw new Error("Either configuration or configPath must be provided");
    }
    if (props.configuration && props.configPath) {
      throw new Error(
        "Only one of configuration or configPath should be provided"
      );
    }

    // Get configuration either from props or load from path
    const config =
      props.configuration ?? this.loadConfigurationFromPath(props.configPath!);

    // Update action groups with executor
    const actionGroups = config.actionGroups.map((group) => ({
      ...group,
      actionGroupExecutor: {
        lambda: props.handlerFunction.functionArn
      }
    }));

    // Create the IAM role for the Bedrock agent
    const agentRole = new Role(this, "AgentRole", {
      assumedBy: new ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Agent"
    });

    agentRole.addToPolicy(
      new PolicyStatement({
        effect: Effect.ALLOW,
        actions: ["bedrock:InvokeModel"],
        resources: [
          `arn:aws:bedrock:${Stack.of(this).region}::foundation-model/${props.foundationModel.modelId}`
        ]
      })
    );

    // Create the Bedrock agent using the configuration
    this.agent = new aws_bedrock.CfnAgent(this, "Default", {
      agentName: `${id}-BedrockAgent`,
      agentResourceRoleArn: agentRole.roleArn,
      foundationModel: props.foundationModel.modelId,
      description: config.description,
      instruction: config.instruction,
      idleSessionTtlInSeconds: props.idleSessionTtlInSeconds ?? 1800,
      actionGroups,
      ...(config.orchestrationConfig && {
        orchestrationConfig: config.orchestrationConfig
      })
    });

    // Create an alias if specified
    if (props.alias) {
      this.agentAlias = new aws_bedrock.CfnAgentAlias(this, "Alias", {
        agentId: this.agent.attrAgentId,
        agentAliasName: props.alias
      });
    }

    // Add Lambda resource-based policy to allow Bedrock agent to invoke the function
    new CfnPermission(this, "BedrockInvocationPermission", {
      action: "lambda:InvokeFunction",
      functionName: props.handlerFunction.functionName,
      principal: "bedrock.amazonaws.com",
      sourceArn: this.agent?.attrAgentArn
    });
  }
}
