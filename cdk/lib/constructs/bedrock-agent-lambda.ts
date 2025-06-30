/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import * as cdk from "aws-cdk-lib";
import * as bedrock from "aws-cdk-lib/aws-bedrock";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as fs from "fs";
import * as path from "path";
import { Construct } from "constructs";

/**
 * Properties for configuring a Bedrock Agent with Lambda-based tools.
 *
 * This interface defines the configuration options for creating a Bedrock Agent
 * that uses a Lambda function to handle agent actions and tools.
 */
export interface BedrockAgentProps {
  /**
   * Optional alias for the agent.
   *
   * If provided, creates an alias pointing to the agent version.
   * This allows for version management and gradual rollouts.
   */
  readonly alias?: string;

  /**
   * The foundation model that will orchestrate the agent's actions.
   *
   * This model is responsible for understanding user queries and determining
   * which tools to invoke based on the agent's capabilities.
   */
  readonly foundationModel: bedrock.FoundationModelIdentifier;

  /**
   * The Lambda function that will handle agent actions and tool execution.
   *
   * This function receives requests from the Bedrock Agent and executes
   * the appropriate tools based on the action group configuration.
   */
  readonly handlerFunction: lambda.IFunction;

  /**
   * Optional idle session timeout in seconds.
   *
   * Defines how long an agent session can remain idle before being terminated.
   * @default 1800 (30 minutes)
   */
  readonly idleSessionTtlInSeconds?: number;

  /**
   * Path to the configuration directory containing agent configuration files.
   *
   * This directory should contain:
   * - `actionGroups/groups.json`: Action group definitions
   * - `description.txt`: Agent description
   * - `instruction.txt`: Agent instructions
   * - `overrides.json`: Optional orchestration configuration overrides
   *
   * Either this or the individual configuration fields must be provided.
   */
  readonly configPath?: string;

  /**
   * Action groups that define the agent's capabilities and available tools.
   *
   * Either this or configPath must be provided.
   */
  readonly actionGroups?: Array<cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty>;

  /**
   * Description of the agent's purpose and capabilities.
   *
   *
   * Either this or configPath must be provided.
   */
  readonly description?: string;

  /**
   * Instructions for the agent on how to behave and respond to user queries.
   *
   * These instructions guide the agent's decision-making process and define
   * its personality and behavior patterns.
   *
   * Either this or configPath must be provided.
   */
  readonly instruction?: string;

  /**
   * Optional orchestration configuration overrides.
   *
   * Allows customization of the agent's orchestration behavior, such as
   * model parameters, response formatting, or other advanced configurations.
   */
  readonly orchestrationConfig?: Record<string, any>;
}

/**
 * A generic L2 construct for creating a Bedrock Agent with tools implemented as a Lambda function.
 *
 * This construct simplifies the creation of Bedrock Agents by providing a high-level
 * interface for configuring the agent, its tools, and the underlying infrastructure.
 *
 * The agent can be configured either by providing individual properties or by
 * loading configuration from a directory structure.
 */
export class BedrockAgentLambda extends Construct {
  /** The underlying Bedrock Agent CloudFormation resource. */
  public readonly agent: cdk.aws_bedrock.CfnAgent;

  /** The agent alias, if one was specified in the configuration. */
  public readonly agentAlias?: cdk.aws_bedrock.CfnAgentAlias;

  /**
   * Loads an agent's configuration from files in a specified directory.
   *
   * Configuration items like action group definitions or specialized prompt
   * templates are logically different from infrastructure settings typically
   * implemented in CDK templates. This method provides a means to separate
   * that material from the CDK code.
   *
   * @param configPath - The root path to agent configuration files.
   * @returns An object containing the loaded configuration.
   * @throws {Error} If any required configuration files are missing or invalid.
   *
   * @private
   */
  private loadConfigurationFromPath(configPath: string): {
    actionGroups: Array<cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty>;
    description: string;
    instruction: string;
    orchestrationConfig?: Record<string, any>;
  } {
    try {
      // Read action groups
      const groupsPath = path.join(configPath, "actionGroups", "groups.json");
      if (!fs.existsSync(groupsPath)) {
        throw new Error(`Action groups file not found at ${groupsPath}`);
      }
      const actionGroups = JSON.parse(fs.readFileSync(groupsPath, "utf8"));

      // Read description
      const descriptionPath = path.join(configPath, "description.txt");
      if (!fs.existsSync(descriptionPath)) {
        throw new Error(`Description file not found at ${descriptionPath}`);
      }
      const description = fs.readFileSync(descriptionPath, "utf8").trim();

      // Read instruction
      const instructionPath = path.join(configPath, "instruction.txt");
      if (!fs.existsSync(instructionPath)) {
        throw new Error(`Instruction file not found at ${instructionPath}`);
      }
      const instruction = fs.readFileSync(instructionPath, "utf8").trim();

      // Read optional orchestration config
      const overridesPath = path.join(configPath, "overrides.json");
      const orchestrationConfig = fs.existsSync(overridesPath)
        ? JSON.parse(fs.readFileSync(overridesPath, "utf8"))
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
   * Creates a new instance of a Bedrock Agent with Lambda-based tools.
   *
   * @param scope - The scope/stack in which to define this construct.
   * @param id - The unique identifier of this construct within the current scope.
   * @param props - The configuration properties for this Bedrock Agent.
   *
   * @throws {Error} If the configuration is invalid (missing required fields or conflicting options).
   */
  constructor(scope: Construct, id: string, props: BedrockAgentProps) {
    super(scope, id);

    // Validate that either configPath or individual configuration fields are provided
    const hasConfigPath = !!props.configPath;
    const hasIndividualConfig = !!(
      props.actionGroups &&
      props.description &&
      props.instruction
    );

    if (!hasConfigPath && !hasIndividualConfig) {
      throw new Error(
        "Either configPath or actionGroups, description, and instruction must be provided"
      );
    }
    if (hasConfigPath && hasIndividualConfig) {
      throw new Error(
        "Only one of configPath or individual configuration fields should be provided"
      );
    }

    // Get configuration either from props or load from path
    let actionGroups: Array<cdk.aws_bedrock.CfnAgent.AgentActionGroupProperty>;
    let description: string;
    let instruction: string;
    let orchestrationConfig: Record<string, any> | undefined;

    if (props.configPath) {
      const config = this.loadConfigurationFromPath(props.configPath);
      actionGroups = config.actionGroups;
      description = config.description;
      instruction = config.instruction;
      orchestrationConfig = config.orchestrationConfig;
    } else {
      actionGroups = props.actionGroups!;
      description = props.description!;
      instruction = props.instruction!;
      orchestrationConfig = props.orchestrationConfig;
    }

    // Update action groups with executor
    const updatedActionGroups = actionGroups.map((group) => ({
      ...group,
      actionGroupExecutor: {
        lambda: props.handlerFunction.functionArn
      }
    }));

    // Create the IAM role for the Bedrock agent with specific permissions
    const agentRole = new iam.Role(this, "AgentRole", {
      assumedBy: new iam.ServicePrincipal("bedrock.amazonaws.com"),
      description:
        "Role for Bedrock Agent with specific model invocation permissions",
      inlinePolicies: {
        BedrockModelInvocationPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ["bedrock:InvokeModel"],
              resources: [
                `arn:aws:bedrock:${cdk.Stack.of(this).region}::foundation-model/${props.foundationModel.modelId}`
              ]
            })
          ]
        })
      }
    });

    // Create the Bedrock agent using the configuration
    this.agent = new cdk.aws_bedrock.CfnAgent(this, "Default", {
      agentName: `${id}-BedrockAgent`,
      agentResourceRoleArn: agentRole.roleArn,
      foundationModel: props.foundationModel.modelId,
      description: description,
      instruction: instruction,
      idleSessionTtlInSeconds: props.idleSessionTtlInSeconds ?? 1800,
      actionGroups: updatedActionGroups,
      ...(orchestrationConfig && { orchestrationConfig: orchestrationConfig })
    });

    // Create an alias if specified
    if (props.alias) {
      this.agentAlias = new cdk.aws_bedrock.CfnAgentAlias(this, "Alias", {
        agentId: this.agent.attrAgentId,
        agentAliasName: props.alias
      });
    }

    // Add Lambda resource-based policy to allow Bedrock agent to invoke the function
    new lambda.CfnPermission(this, "BedrockInvocationPermission", {
      action: "lambda:InvokeFunction",
      functionName: props.handlerFunction.functionName,
      principal: "bedrock.amazonaws.com",
      sourceArn: this.agent?.attrAgentArn
    });
  }
}
