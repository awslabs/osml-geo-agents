#!/usr/bin/env bash
# Copyright 2026 Amazon.com, Inc. or its affiliates.
#
# Destroys CDK stacks in the correct order:
#   1. Dataplane and IntegrationTest in parallel
#   2. Network stack last since both above stacks depend on it
#
# Usage: ./scripts/destroy.sh <project_name>
#   project_name: CDK project name prefix (e.g. OSML-GeoAgent)

set -euo pipefail

PROJECT_NAME="${1:?Usage: $0 <project_name>}"

cdk destroy "${PROJECT_NAME}-Dataplane" --exclusively --app cdk.out --force &
PID_DP=$!

PID_IT=""
if aws cloudformation describe-stacks --stack-name "${PROJECT_NAME}-IntegrationTest" > /dev/null 2>&1; then
  cdk destroy "${PROJECT_NAME}-IntegrationTest" --exclusively --app cdk.out --force &
  PID_IT=$!
else
  echo "Integration test stack not found or not accessible, skipping"
fi

FAILED=0
wait ${PID_DP} || { echo "::error::Dataplane stack destroy failed"; FAILED=1; }
if [ -n "${PID_IT}" ]; then
  wait ${PID_IT} || { echo "::error::IntegrationTest stack destroy failed"; FAILED=1; }
fi

if [ ${FAILED} -ne 0 ]; then
  echo "::error::One or more stack destroys failed"
  exit 1
fi

cdk destroy "${PROJECT_NAME}-Network" --exclusively --app cdk.out --force
