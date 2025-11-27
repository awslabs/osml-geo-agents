/*
 * Copyright 2025 Amazon.com, Inc. or its affiliates.
 */

/**
 * OSML Account configuration interface.
 */
export interface OSMLAccount {
  /** The AWS account ID. */
  readonly id: string;
  /** The AWS region. */
  readonly region: string;
  /** Whether this is a production-like environment. */
  readonly prodLike: boolean;
  /** Whether this is an ADC (Amazon Dedicated Cloud) environment. */
  readonly isAdc: boolean;
}

/**
 * Base configuration type for OSML constructs.
 */
export type ConfigType = Record<string, unknown>;

/**
 * Base configuration class for OSML constructs.
 */
export abstract class BaseConfig {
  /**
   * Constructor for BaseConfig.
   *
   * @param config - The configuration object
   */
  constructor(config: Partial<ConfigType> = {}) {
    Object.assign(this, config);
  }
}
