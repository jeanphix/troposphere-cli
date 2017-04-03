from troposphere import (
    Output,
    Parameter,
    Template,
)
from troposphere.s3 import Bucket


stack = Template()


stack.add_parameter(Parameter(
    "FirstParameter",
    Type="String",
))


stack.add_parameter(Parameter(
    "SecondParameter",
    Type="String",
))


bucket = stack.add_resource(Bucket("MyBucket"))


stack.add_output(Output(
    "FirstOutput",
    Description="First output",
    Value="A value",
))

stack.add_output(Output(
    "SecondOutput",
    Description="First output",
    Value="Another value",
))
