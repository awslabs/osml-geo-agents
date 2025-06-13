/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

import { App } from "aws-cdk-lib";

interface ComponentConfig {
    /**
     * Configuration options for the component.
     */
    config?: { [key: string]: unknown };
}

interface OSMLAccount {
    /**
     * Account number of the AWS account.
     */
    id: string;

    /**
     * AWS Region (ex. us-west-2).
     */
    region: string;
}

/**
 * Configuration class for the CDK application.
 */
export class AppConfig {
    /**
     * The CDK application instance.
     */
    app: App;

    /**
     * The name of the project.
     */
    projectName: string;

    /**
     * The AWS account configuration.
     */
    account: OSMLAccount;

    /**
     * Configuration for the geo agent component.
     */
    geoAgent: ComponentConfig;

    /**
     * Constructs a new AppConfig instance.
     *
     * @param app - The CDK application instance.
     */
    constructor(app: App) {
        this.app = app;
        this.projectName = this.getContextValue("projectName");
        this.account = this.getContextValue("account");
        this.geoAgent = this.getContextValue("geoAgent", true);
    }

    /**
     * Retrieves the context value for a given key.
     *
     * @param key - The context key to retrieve.
     * @param optional - Whether the context key is optional.
     * @returns The context value.
     * @throws Will throw an error if the context key is not found and is not optional.
     */
    private getContextValue<T>(key: string, optional: boolean = false): T {
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        const value = this.app.node.tryGetContext(key);
        if (value === undefined && !optional) {
            throw new Error(`Context value for key "${key}" is not defined.`);
        }
        return value as T;
    }
}

// Initialize the default CDK application and configure it
export const appConfig = new AppConfig(new App());
