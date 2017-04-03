import boto3

from unittest import TestCase

from click.testing import CliRunner
from moto.cloudformation import mock_cloudformation
from moto.cloudformation.models import cloudformation_backends


from ..cli import (
    create,
    list,
    outputs,
    parameters,
    template,
    update,
)


template_json = """{
    "Outputs": {
        "FirstOutput": {
            "Description": "First output",
            "Value": "A value"
        },
        "SecondOutput": {
            "Description": "First output",
            "Value": "Another value"
        }
    },
    "Parameters": {
        "FirstParameter": {
            "Type": "String"
        },
        "SecondParameter": {
            "Type": "String"
        }
    },
    "Resources": {
        "MyBucket": {
            "Type": "AWS::S3::Bucket"
        }
    }
}
"""


template_path = 'trop.tests.stack.stack'
region = 'eu-west-1'


class TropTest(TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def mock_stack(self, name):
        backend = cloudformation_backends[region]
        return backend.create_stack(
            name,
            template_json,
            dict(FirstParameter="Value", SecondParameter="AnotherValue"),
            region,
        )

    def invoke(self, command, *args, template_path=template_path):
        client = boto3.client('cloudformation', region_name=region)

        if template_path is not None:
            args = args + (
                '--template',
                template_path,
            )

        return self.runner.invoke(
            command,
            args,
            catch_exceptions=False,
            obj=client,
        )

    def test_create(self):
        with mock_cloudformation():
            result = self.invoke(
                create,
                'my-stack',
                "--tail",
                '--parameter',
                'FirstParameter',
                'Value',
                '--parameter',
                'SecondParameter',
                'AnotherValue',
            )

        self.assertEqual(result.exit_code, 0)
        self.assertIn(
            "[ my-stack             ] CREATE_COMPLETE",
            result.output,
        )

    def test_list(self):
        with mock_cloudformation():
            self.mock_stack('my-stack')

            result = self.invoke(
                list,
                template_path=None,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertIn(
                "my-stack        CREATE_COMPLETE",
                result.output,
            )

    def test_update(self):
        with mock_cloudformation():
            self.mock_stack('my-stack')

            result = self.invoke(
                update,
                'my-stack',
                "--tail",
                '--parameter',
                'FirstParameter',
                'Value',
                '--parameter',
                'SecondParameter',
                'AnotherValue',
            )

            self.assertEqual(result.exit_code, 0)
            self.assertIn(
                "[ my-stack             ] UPDATE_COMPLETE",
                result.output,
            )

    def test_outputs_all(self):
        with mock_cloudformation():
            self.mock_stack('my-stack')

            result = self.invoke(
                outputs,
                'my-stack',
                template_path=None,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertIn(
                "FirstOutput                        : A value",
                result.output,
            )
            self.assertIn(
                "SecondOutput                       : Another value",
                result.output,
            )

    def test_outputs_specific_key(self):
        with mock_cloudformation():
            self.mock_stack('my-stack')

            result = self.invoke(
                outputs,
                'my-stack',
                '--key',
                'SecondOutput',
                template_path=None,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(
                "Another value\n",
                result.output,
            )

    def test_parameters_all(self):
        with mock_cloudformation():
            self.mock_stack('my-stack')

            result = self.invoke(
                parameters,
                'my-stack',
                template_path=None,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertIn(
                "FirstParameter                     : Value",
                result.output,
            )
            self.assertIn(
                "SecondParameter                    : AnotherValue",
                result.output,
            )

    def test_template(self):
        result = self.runner.invoke(template, [template_path])
        self.assertEqual(result.output, template_json)
        self.assertEqual(result.exit_code, 0)
