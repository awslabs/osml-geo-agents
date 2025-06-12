#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import patch


class TestLambdaEventHandler(unittest.TestCase):
    @patch.dict("os.environ", {"WORKSPACE_BUCKET_NAME": "test_workspace_bucket"})
    def test_valid_import(self):
        from aws.osml.geoagents.bedrock import handler  # noqa: F401
