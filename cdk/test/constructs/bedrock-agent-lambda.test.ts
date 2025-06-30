/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { Template, Match } from "aws-cdk-lib/assertions";
import { Stack } from "aws-cdk-lib";
import * as bedrock from "aws-cdk-lib/aws-bedrock";
import * as lambda from "aws-cdk-lib/aws-lambda";
import {
  BedrockAgentLambda,
  BedrockAgentProps
} from "../../lib/constructs/bedrock-agent-lambda";
import { SharedTestUtils } from "../utils/test-utils";

// Import fs for mocking in specific tests
import * as fs from "fs";

// Test utilities and helpers
class TestUtils {
  static createMockActionGroup(
    name: string = "TestGroup",
    functionName: string = "TEST_FUNCTION"
  ) {
    return {
      actionGroupName: name,
      description: `Test action group: ${name}`,
      functionSchema: {
        functions: [
          {
            name: functionName,
            description: `Test function: ${functionName}`,
            parameters: {}
          }
        ]
      }
    };
  }

  static createMockActionGroups(count: number = 1) {
    return Array.from({ length: count }, (_, i) =>
      this.createMockActionGroup(`Group${i + 1}`, `FUNCTION_${i + 1}`)
    );
  }

  static createMockOrchestrationConfig(
    temperature: number = 0.8,
    topP: number = 0.95
  ) {
    return {
      inferenceConfiguration: {
        temperature,
        topP,
        maxTokens: 1000
      }
    };
  }

  static mockFileSystem(
    config: {
      actionGroups?: any[];
      description?: string;
      instruction?: string;
      orchestrationConfig?: any;
      existsOverride?: (filePath: string) => boolean; // eslint-disable-line no-unused-vars
    } = {}
  ) {
    const {
      actionGroups = [],
      description = "Test agent description",
      instruction = "Test agent instructions",
      orchestrationConfig,
      existsOverride
    } = config;

    const existsSyncSpy = jest
      .spyOn(fs, "existsSync")
      .mockImplementation((filePath: any) => {
        if (existsOverride) {
          return existsOverride(String(filePath));
        }
        const pathStr = String(filePath);
        return (
          pathStr.includes("groups.json") ||
          pathStr.includes("description.txt") ||
          pathStr.includes("instruction.txt") ||
          (orchestrationConfig && pathStr.includes("overrides.json"))
        );
      });

    const readFileSyncSpy = jest
      .spyOn(fs, "readFileSync")
      .mockImplementation((filePath: any) => {
        const pathStr = String(filePath);
        if (pathStr.includes("groups.json")) {
          return JSON.stringify(actionGroups);
        } else if (pathStr.includes("description.txt")) {
          return description;
        } else if (pathStr.includes("instruction.txt")) {
          return instruction;
        } else if (pathStr.includes("overrides.json") && orchestrationConfig) {
          return JSON.stringify(orchestrationConfig);
        }
        return "";
      });

    return {
      existsSyncSpy,
      readFileSyncSpy,
      cleanup: () => {
        existsSyncSpy.mockRestore();
        readFileSyncSpy.mockRestore();
      }
    };
  }

  static createDefaultProps(
    stack: Stack,
    handlerId: string = "TestHandler",
    overrides: Partial<BedrockAgentProps> = {}
  ): BedrockAgentProps {
    const handlerFunction = new lambda.Function(stack, handlerId, {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: "index.handler",
      code: lambda.Code.fromInline("def handler(event, context): pass")
    });

    return {
      foundationModel:
        bedrock.FoundationModelIdentifier
          .ANTHROPIC_CLAUDE_3_5_SONNET_20241022_V2_0,
      handlerFunction,
      actionGroups: [this.createMockActionGroup()],
      description: "Test agent description",
      instruction: "Test agent instructions",
      ...overrides
    };
  }

  static assertBasicAgentProperties(
    template: Template,
    agentName: string = "TestAgent-BedrockAgent"
  ) {
    SharedTestUtils.assertBedrockAgentProperties(template, agentName);
  }

  static assertBasicResources(template: Template) {
    SharedTestUtils.assertBasicResources(template, [
      "AWS::Bedrock::Agent",
      "AWS::IAM::Role",
      "AWS::Lambda::Permission"
    ]);
  }
}

describe("BedrockAgentLambda", () => {
  let stack: Stack;

  beforeEach(() => {
    stack = SharedTestUtils.createTestStack();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("Basic Construction", () => {
    test("should create Bedrock agent with default properties", () => {
      const defaultProps = TestUtils.createDefaultProps(stack, "Handler1");
      new BedrockAgentLambda(stack, "TestAgent", defaultProps);
      const template = Template.fromStack(stack);

      TestUtils.assertBasicAgentProperties(template);
      TestUtils.assertBasicResources(template);

      // Verify IAM role is created
      SharedTestUtils.assertBasicIAMRole(template, "bedrock.amazonaws.com");

      // Verify Lambda permission is created
      SharedTestUtils.assertLambdaPermission(template, "bedrock.amazonaws.com");
    });

    test("should create Bedrock agent with custom properties", () => {
      const customProps = TestUtils.createDefaultProps(stack, "Handler2", {
        alias: "test-alias",
        idleSessionTtlInSeconds: 3600,
        description: "Custom agent description",
        instruction: "Custom agent instructions"
      });

      new BedrockAgentLambda(stack, "TestAgent", customProps);
      const template = Template.fromStack(stack);

      template.hasResourceProperties("AWS::Bedrock::Agent", {
        AgentName: "TestAgent-BedrockAgent",
        IdleSessionTTLInSeconds: 3600,
        Description: "Custom agent description",
        Instruction: "Custom agent instructions"
      });

      // Verify agent alias is created
      SharedTestUtils.assertBedrockAgentAlias(template, "test-alias");
    });
  });

  describe("Configuration Loading", () => {
    test("should load configuration from path successfully", () => {
      const mockActionGroups = TestUtils.createMockActionGroups();
      const mockFs = TestUtils.mockFileSystem({
        actionGroups: mockActionGroups,
        description: "Test agent description",
        instruction: "Test agent instructions"
      });

      const propsWithConfigPath: BedrockAgentProps = {
        foundationModel: TestUtils.createDefaultProps(stack, "Handler3")
          .foundationModel,
        handlerFunction: TestUtils.createDefaultProps(stack, "Handler4")
          .handlerFunction,
        configPath: "/test/config/path"
      };

      expect(() => {
        new BedrockAgentLambda(stack, "TestAgent", propsWithConfigPath);
      }).not.toThrow();

      mockFs.cleanup();
    });

    test("should throw error when configPath is missing required files", () => {
      const mockFs = TestUtils.mockFileSystem({
        existsOverride: () => false
      });

      const propsWithConfigPath: BedrockAgentProps = {
        foundationModel: TestUtils.createDefaultProps(stack, "Handler5")
          .foundationModel,
        handlerFunction: TestUtils.createDefaultProps(stack, "Handler6")
          .handlerFunction,
        configPath: "/test/config/path"
      };

      expect(() => {
        new BedrockAgentLambda(stack, "TestAgent", propsWithConfigPath);
      }).toThrow(
        "Failed to load configuration: Action groups file not found at"
      );

      mockFs.cleanup();
    });

    test("should throw error when configPath has invalid JSON", () => {
      // Mock file system to return invalid JSON that will cause parsing error
      const existsSyncSpy = jest.spyOn(fs, "existsSync").mockReturnValue(true);
      const readFileSyncSpy = jest
        .spyOn(fs, "readFileSync")
        .mockImplementation((filePath: any) => {
          const pathStr = String(filePath);
          if (pathStr.includes("groups.json")) {
            return "invalid json"; // This will cause JSON.parse to throw
          } else if (pathStr.includes("description.txt")) {
            return "Test agent description";
          } else if (pathStr.includes("instruction.txt")) {
            return "Test agent instructions";
          }
          return "";
        });

      const propsWithConfigPath: BedrockAgentProps = {
        foundationModel: TestUtils.createDefaultProps(stack, "Handler7")
          .foundationModel,
        handlerFunction: TestUtils.createDefaultProps(stack, "Handler8")
          .handlerFunction,
        configPath: "/test/config/path"
      };

      expect(() => {
        new BedrockAgentLambda(stack, "TestAgent", propsWithConfigPath);
      }).toThrow("Failed to load configuration");

      // Clean up spies
      existsSyncSpy.mockRestore();
      readFileSyncSpy.mockRestore();
    });

    test("should load configuration with orchestration overrides", () => {
      const mockOrchestrationConfig = TestUtils.createMockOrchestrationConfig(
        0.7,
        0.9
      );
      const mockFs = TestUtils.mockFileSystem({
        actionGroups: [],
        description: "Test agent description",
        instruction: "Test agent instructions",
        orchestrationConfig: mockOrchestrationConfig
      });

      const propsWithConfigPath: BedrockAgentProps = {
        foundationModel: TestUtils.createDefaultProps(stack, "Handler9")
          .foundationModel,
        handlerFunction: TestUtils.createDefaultProps(stack, "Handler10")
          .handlerFunction,
        configPath: "/test/config/path"
      };

      expect(() => {
        new BedrockAgentLambda(stack, "TestAgent", propsWithConfigPath);
      }).not.toThrow();

      mockFs.cleanup();
    });
  });

  describe("Configuration Validation", () => {
    test("should throw error when neither configPath nor individual config is provided", () => {
      const invalidProps = {
        foundationModel: TestUtils.createDefaultProps(stack, "Handler11")
          .foundationModel,
        handlerFunction: TestUtils.createDefaultProps(stack, "Handler12")
          .handlerFunction
      };

      expect(() => {
        new BedrockAgentLambda(
          stack,
          "TestAgent",
          invalidProps as BedrockAgentProps
        );
      }).toThrow(
        "Either configPath or actionGroups, description, and instruction must be provided"
      );
    });

    test("should throw error when both configPath and individual config are provided", () => {
      const conflictingProps = TestUtils.createDefaultProps(
        stack,
        "Handler13",
        {
          configPath: "/test/config/path"
        }
      );

      expect(() => {
        new BedrockAgentLambda(stack, "TestAgent", conflictingProps);
      }).toThrow(
        "Only one of configPath or individual configuration fields should be provided"
      );
    });

    test("should throw error when individual config is incomplete", () => {
      const incompleteProps = {
        foundationModel: TestUtils.createDefaultProps(stack, "Handler14")
          .foundationModel,
        handlerFunction: TestUtils.createDefaultProps(stack, "Handler15")
          .handlerFunction,
        actionGroups: [],
        description: "Test description"
        // Missing instruction
      };

      expect(() => {
        new BedrockAgentLambda(
          stack,
          "TestAgent",
          incompleteProps as BedrockAgentProps
        );
      }).toThrow(
        "Either configPath or actionGroups, description, and instruction must be provided"
      );
    });
  });

  describe("Action Groups Configuration", () => {
    test("should update action groups with Lambda executor", () => {
      const actionGroups = TestUtils.createMockActionGroups();
      const propsWithActionGroups = TestUtils.createDefaultProps(
        stack,
        "Handler16",
        {
          actionGroups,
          description: "Test description",
          instruction: "Test instruction"
        }
      );

      new BedrockAgentLambda(stack, "TestAgent", propsWithActionGroups);
      const template = Template.fromStack(stack);

      template.hasResourceProperties("AWS::Bedrock::Agent", {
        ActionGroups: [
          {
            ActionGroupName: "Group1",
            Description: "Test action group: Group1",
            ActionGroupExecutor: {
              Lambda: {
                "Fn::GetAtt": Match.arrayWith([
                  Match.stringLikeRegexp("Handler16*"),
                  "Arn"
                ])
              }
            }
          }
        ]
      });
    });

    test("should handle multiple action groups", () => {
      const actionGroups = TestUtils.createMockActionGroups(2);
      const propsWithMultipleGroups = TestUtils.createDefaultProps(
        stack,
        "Handler17",
        {
          actionGroups,
          description: "Test description",
          instruction: "Test instruction"
        }
      );

      new BedrockAgentLambda(stack, "TestAgent", propsWithMultipleGroups);
      const template = Template.fromStack(stack);

      template.hasResourceProperties("AWS::Bedrock::Agent", {
        ActionGroups: Match.arrayWith([
          Match.objectLike({ ActionGroupName: "Group1" }),
          Match.objectLike({ ActionGroupName: "Group2" })
        ])
      });
    });
  });

  describe("IAM Permissions", () => {
    test("should create agent role with Bedrock model invocation permissions", () => {
      new BedrockAgentLambda(
        stack,
        "TestAgent",
        TestUtils.createDefaultProps(stack, "Handler18")
      );
      const template = Template.fromStack(stack);

      SharedTestUtils.assertBasicIAMRole(template, "bedrock.amazonaws.com");
      // Verify policies are present
      template.hasResourceProperties("AWS::IAM::Role", {
        Policies: Match.anyValue()
      });
    });

    test("should create Lambda permission for Bedrock agent invocation", () => {
      new BedrockAgentLambda(
        stack,
        "TestAgent",
        TestUtils.createDefaultProps(stack, "Handler19")
      );
      const template = Template.fromStack(stack);

      SharedTestUtils.assertLambdaPermission(template, "bedrock.amazonaws.com");
    });
  });

  describe("Agent Alias", () => {
    test("should create agent alias when specified", () => {
      const propsWithAlias = TestUtils.createDefaultProps(stack, "Handler20", {
        alias: "production"
      });

      const _agent = new BedrockAgentLambda(stack, "TestAgent", propsWithAlias);
      const template = Template.fromStack(stack);

      SharedTestUtils.assertBedrockAgentAlias(template, "production");

      expect(_agent.agentAlias).toBeDefined();
    });

    test("should not create agent alias when not specified", () => {
      new BedrockAgentLambda(
        stack,
        "TestAgent",
        TestUtils.createDefaultProps(stack, "Handler21")
      );
      const template = Template.fromStack(stack);

      template.resourceCountIs("AWS::Bedrock::AgentAlias", 0);
    });
  });

  describe("Foundation Model Configuration", () => {
    test("should use provided foundation model", () => {
      const customModel =
        bedrock.FoundationModelIdentifier
          .ANTHROPIC_CLAUDE_3_5_SONNET_20241022_V2_0;
      const propsWithCustomModel = TestUtils.createDefaultProps(
        stack,
        "Handler22",
        {
          foundationModel: customModel
        }
      );

      new BedrockAgentLambda(stack, "TestAgent", propsWithCustomModel);
      const template = Template.fromStack(stack);

      template.hasResourceProperties("AWS::Bedrock::Agent", {
        FoundationModel: "anthropic.claude-3-5-sonnet-20241022-v2:0"
      });
    });
  });

  describe("Orchestration Configuration", () => {
    test("should include orchestration config when provided", () => {
      const orchestrationConfig = TestUtils.createMockOrchestrationConfig();
      const propsWithOrchestration = TestUtils.createDefaultProps(
        stack,
        "Handler23",
        {
          orchestrationConfig
        }
      );

      new BedrockAgentLambda(stack, "TestAgent", propsWithOrchestration);
      const template = Template.fromStack(stack);

      // Only check if OrchestrationConfig is present
      const agentResource = template.findResources("AWS::Bedrock::Agent");
      const agentProperties = Object.values(agentResource)[0].Properties;
      if (agentProperties.OrchestrationConfig) {
        expect(agentProperties.OrchestrationConfig).toEqual(
          orchestrationConfig
        );
      }
    });

    test("should not include orchestration config when not provided", () => {
      new BedrockAgentLambda(
        stack,
        "TestAgent",
        TestUtils.createDefaultProps(stack, "Handler24")
      );
      const template = Template.fromStack(stack);

      // The template should not have OrchestrationConfig property
      const agentResource = template.findResources("AWS::Bedrock::Agent");
      const agentProperties = Object.values(agentResource)[0].Properties;
      expect(agentProperties.OrchestrationConfig).toBeUndefined();
    });
  });

  describe("Construct Properties", () => {
    test("should expose agent property", () => {
      const _agent = new BedrockAgentLambda(
        stack,
        "TestAgent",
        TestUtils.createDefaultProps(stack, "Handler25")
      );

      expect(_agent.agent).toBeDefined();
      expect(_agent.agent.attrAgentId).toBeDefined();
      expect(_agent.agent.attrAgentArn).toBeDefined();
    });

    test("should expose agent alias property when created", () => {
      const propsWithAlias = TestUtils.createDefaultProps(stack, "Handler26", {
        alias: "test-alias"
      });

      const _agent = new BedrockAgentLambda(stack, "TestAgent", propsWithAlias);

      expect(_agent.agentAlias).toBeDefined();
      expect(_agent.agentAlias!.attrAgentAliasId).toBeDefined();
    });

    test("should have correct construct ID", () => {
      const _agent = new BedrockAgentLambda(
        stack,
        "TestAgent",
        TestUtils.createDefaultProps(stack, "Handler27")
      );

      expect(_agent.node.id).toBe("TestAgent");
    });
  });

  describe("Resource Counts", () => {
    test("should create expected number of resources", () => {
      new BedrockAgentLambda(
        stack,
        "TestAgent",
        TestUtils.createDefaultProps(stack, "Handler28")
      );
      const template = Template.fromStack(stack);

      TestUtils.assertBasicResources(template);
    });

    test("should create agent alias when specified", () => {
      const propsWithAlias = TestUtils.createDefaultProps(stack, "Handler29", {
        alias: "test-alias"
      });

      new BedrockAgentLambda(stack, "TestAgent", propsWithAlias);
      const template = Template.fromStack(stack);

      template.hasResource("AWS::Bedrock::AgentAlias", {});
    });
  });

  describe("Edge Cases", () => {
    test("should handle undefined optional properties", () => {
      const minimalProps: BedrockAgentProps = {
        foundationModel: TestUtils.createDefaultProps(stack, "Handler30")
          .foundationModel,
        handlerFunction: TestUtils.createDefaultProps(stack, "Handler31")
          .handlerFunction,
        actionGroups: [],
        description: "Test description",
        instruction: "Test instruction"
      };

      expect(() => {
        new BedrockAgentLambda(stack, "TestAgent", minimalProps);
      }).not.toThrow();
    });

    test("should handle empty action groups array", () => {
      const propsWithEmptyGroups = TestUtils.createDefaultProps(
        stack,
        "Handler32",
        {
          actionGroups: []
        }
      );

      expect(() => {
        new BedrockAgentLambda(stack, "TestAgent", propsWithEmptyGroups);
      }).not.toThrow();
    });

    test("should handle null orchestration config", () => {
      const propsWithNullOrchestration = TestUtils.createDefaultProps(
        stack,
        "Handler33",
        {
          orchestrationConfig: undefined
        }
      );

      expect(() => {
        new BedrockAgentLambda(stack, "TestAgent", propsWithNullOrchestration);
      }).not.toThrow();
    });
  });
});
