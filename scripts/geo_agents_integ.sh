#!/bin/bash
#
# Copyright 2025 Amazon.com, Inc. or its affiliates.
#

set -e  # Exit immediately if a command exits with a non-zero status
set -o pipefail  # Exit if any part of a pipeline fails

print_banner() {
    echo "=========================================="
    echo " Running GeoAgent Integration Tests      "
    echo "=========================================="
}

print_test_passed() {
    echo "=========================================="
    echo "      Integration Tests Completed        "
    echo "=========================================="
    echo "           All tests passed!             "
    echo "=========================================="
}

print_test_failed() {
    echo "=========================================="
    echo "       Integration Tests Failed          "
    echo "=========================================="
    echo "       Some tests did not pass!          "
    echo "=========================================="
}

# Function to handle errors
handle_error() {
    echo "ERROR: An error occurred during the script execution."
    exit 1
}

# Trap errors and call the handle_error function
trap 'handle_error' ERR

# Check AWS_REGION, aws configure, then AWS_DEFAULT_REGION to determine the region.
# If none are set, prompt the user for the AWS_REGION.
if [ -z "$AWS_REGION" ]; then
    {
        AWS_REGION=$(aws configure get region)
    } || {
        if [ -n "$AWS_DEFAULT_REGION" ]; then
            AWS_REGION=$AWS_DEFAULT_REGION
        else
            read -p "Could not find region. Enter the AWS region (ex. us-west-2): " user_region
            if [ -n "$user_region" ]; then
                AWS_REGION=$user_region
            else
                echo "ERROR: AWS region is required."
                exit 1
            fi
        fi
    }
fi

# Grab the account id for the loaded AWS credentials
ACCOUNT_ID=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)

# Check if the account ID was successfully retrieved.
# If not, prompt the user for the account ID.
if [ -z "$ACCOUNT_ID" ]; then
    read -p "Please enter your AWS Account ID: " account_id
    if [ -z "$account_id" ]; then
        echo "ERROR: AWS Account ID is required."
        exit 1
    else
        ACCOUNT_ID=$account_id
    fi
fi

# Print the starting banner
print_banner

# Create the lambda test payload (empty for now, can be extended later)
TEMP_PAYLOAD=$(mktemp)
echo "{}" > "$TEMP_PAYLOAD"

echo "Invoking the Lambda function 'GeoAgentTestRunner'"
echo "Region: $AWS_REGION"
echo ""

# Invoke the Lambda function and capture the request ID
RESPONSE_FILE=$(mktemp)
if ! aws lambda invoke --region "$AWS_REGION" \
                       --function-name "GeoAgentTestRunner" \
                       --payload fileb://"$TEMP_PAYLOAD" \
                       --cli-read-timeout 0 \
                       "$RESPONSE_FILE" > /dev/null 2>&1; then
    echo "ERROR: Failed to invoke Lambda function"
    rm -f "$TEMP_PAYLOAD" "$RESPONSE_FILE"
    exit 1
fi

echo "Lambda invoked successfully, retrieving full logs from CloudWatch..."
echo ""

# Disable error trap and pipefail for CloudWatch section
trap - ERR
set +e
set +o pipefail

# Wait for logs to be available and fully written to CloudWatch
echo "Waiting for CloudWatch logs to propagate..."
sleep 10

# Get the most recent log stream for this Lambda function
LOG_GROUP="/aws/lambda/GeoAgentTestRunner"

# List recent log streams for debugging
echo "Fetching recent log streams..."
LOG_STREAMS_LIST=$(aws logs describe-log-streams \
    --region "$AWS_REGION" \
    --log-group-name "$LOG_GROUP" \
    --order-by LastEventTime \
    --descending \
    --max-items 3 \
    --output json 2>&1)
DESCRIBE_EXIT=$?

if [ $DESCRIBE_EXIT -ne 0 ]; then
    echo "ERROR: Failed to describe log streams"
    echo "$LOG_STREAMS_LIST"
    rm -f "$TEMP_PAYLOAD" "$RESPONSE_FILE"
    exit 1
fi

# Extract the most recent log stream name
LOG_STREAM=$(echo "$LOG_STREAMS_LIST" | jq -r '.logStreams[0].logStreamName' 2>&1)

if [ -z "$LOG_STREAM" ] || [ "$LOG_STREAM" == "null" ] || [ "$LOG_STREAM" == "None" ]; then
    echo "ERROR: Could not find log stream for Lambda function"
    echo "Available log streams:"
    echo "$LOG_STREAMS_LIST" | jq -r '.logStreams[].logStreamName' 2>&1
    rm -f "$TEMP_PAYLOAD" "$RESPONSE_FILE"
    exit 1
fi

echo "Using log stream: $LOG_STREAM"

# Poll for complete logs (wait for END RequestId marker)
MAX_ATTEMPTS=12
ATTEMPT=0
decoded_log=""

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))

    log_events_json=$(aws logs get-log-events \
        --region "$AWS_REGION" \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$LOG_STREAM" \
        --start-from-head \
        --output json 2>&1)

    if [ $? -eq 0 ]; then
        decoded_log=$(echo "$log_events_json" | jq -r '.events[].message')

        # Check if logs are complete (contains END RequestId)
        if echo "$decoded_log" | grep -q "END RequestId:"; then
            echo "Logs retrieved successfully."
            break
        fi
    fi

    if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
        echo "Waiting for complete logs... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
        sleep 2
    fi
done

if [ -z "$decoded_log" ] || ! echo "$decoded_log" | grep -q "END RequestId:"; then
    echo "ERROR: Could not retrieve complete logs from CloudWatch"
    rm -f "$TEMP_PAYLOAD" "$RESPONSE_FILE"
    exit 1
fi

# Clean up temporary files
rm -f "$RESPONSE_FILE"

# Note: Keeping error handling disabled for log parsing section
# to allow graceful handling of missing patterns

# Extract just the test counts line from JSON log messages
# The logger outputs nested JSON, so parse both levels
test_summary=$(echo "$log_events_json" | jq -r '.events[] | select(.message | contains("Tests:")) | .message' | while read -r line; do
    # Try to parse as JSON to get inner message field
    inner_msg=$(echo "$line" | jq -r '.message' 2>/dev/null || echo "$line")
    echo "$inner_msg"
done | head -1)

# Clean up the temporary payload file
rm -f "$TEMP_PAYLOAD"

# Check for success in the decoded log
if echo "$decoded_log" | grep -q "Success: 100.00%"; then
    echo "$test_summary"
    echo ""
    print_test_passed
    exit 0
else
    # If failed, display test counts and pytest's short test summary
    print_test_failed
    echo ""
    echo "$test_summary"
    echo ""

    # Extract the pytest short test summary section
    # Match lines between header and footer (inclusive of both)
    pytest_summary=$(echo "$decoded_log" | awk '
        /short test summary info/ {p=1; print; next}
        p==1 && /(failed|passed) in [0-9]+\.[0-9]+s/ {print; exit}
        p==1 {print}
    ')

    if [ -n "$pytest_summary" ]; then
        echo "$pytest_summary"
    else
        echo "Could not extract test failure details from logs."
    fi

    exit 1
fi
