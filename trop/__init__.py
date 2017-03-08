import os
import sys
import click
import boto3
import time

from datetime import (
    datetime,
    timedelta,
)
from pytz import utc
from botocore.exceptions import ClientError

from functools import update_wrapper
from troposphere import Template


@click.group()
@click.option(
    '--region',
    '-r',
    envvar='AWS_REGION',
    required=True,
    help="The `AWS` region.",
)
@click.pass_context
def cli(context, region):
    """ Troposphere CLI.
    """
    context.obj = boto3.client('cloudformation', region_name=region)


STATUSES = [
    'CREATE_IN_PROGRESS',
    'CREATE_FAILED',
    'CREATE_COMPLETE',
    'ROLLBACK_IN_PROGRESS',
    'ROLLBACK_FAILED',
    'ROLLBACK_COMPLETE',
    'DELETE_IN_PROGRESS',
    'DELETE_FAILED',
    'DELETE_COMPLETE',
    'UPDATE_IN_PROGRESS',
    'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
    'UPDATE_COMPLETE',
    'UPDATE_ROLLBACK_IN_PROGRESS',
    'UPDATE_ROLLBACK_FAILED',
    'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
    'UPDATE_ROLLBACK_COMPLETE',
]


@cli.command()
@click.option('--all', is_flag=True)
@click.pass_obj
def list(client, all):
    """ List stacks.
    """
    statuses = STATUSES.copy()
    if not all:
        statuses.remove('DELETE_COMPLETE')

    stacks = client.list_stacks(
        StackStatusFilter=statuses,
    )
    for stack in stacks.get('StackSummaries'):
        click.echo(
            "%(StackName)-15s %(StackStatus)s" % stack
        )


def _events(client, name):
    now = utc.localize(datetime.utcnow())
    seen = set()

    while True:
        status = (
            client.describe_stacks(StackName=name)
            .get('Stacks')[0]
            .get('StackStatus')
        )

        events = client.describe_stack_events(StackName=name)

        for event in reversed(events.get('StackEvents')):
            id = event.get('EventId')
            timestamp = event.get('Timestamp')

            if timestamp < now - timedelta(seconds=2):
                continue

            if id not in seen:
                message = (
                    "%(Timestamp)s [ %(LogicalResourceId)-20s ] "
                    % event +
                    "%(ResourceStatus)s"
                    % event
                )
                reason = event.get('ResourceStatusReason')

                if reason is not None:
                    message += " - %s" % reason

                click.echo(message)

            seen.add(id)

        if status.endswith('COMPLETE'):
            break

        time.sleep(1)


@cli.command()
@click.argument('name')
@click.pass_obj
def events(*args, **kwargs):
    """ Display stack events.
    """
    return _events(*args, **kwargs)


@cli.command()
@click.argument('name')
@click.option(
    '--key',
    '-k',
    help="Output the value for given key.",
)
@click.pass_obj
def outputs(client, name, key=None):
    """ Show stack output values.
    """
    for output in (
        client.describe_stacks(StackName=name)
        .get('Stacks')[0]
        .get('Outputs')
    ):
        if key is not None:
            if output.get('OutputKey') == key:
                click.echo(output.get('OutputValue'))
                break

            continue

        click.echo(
            "%(OutputKey)-35s: %(OutputValue)-30s" % output
        )


def _parameters(client, name):
    stack = client.describe_stacks(StackName=name).get('Stacks')[0]
    assert stack.get('StackStatus') not in (
        'DELETE_COMPLETE',
    )

    return {
        parameter['ParameterKey']: parameter['ParameterValue']
        for parameter in stack.get('Parameters')
    }


@cli.command()
@click.argument('name')
@click.pass_obj
def parameters(client, name):
    """ Show templates parameter values.
    """
    try:
        for key, value in _parameters(client, name).items():
            click.echo(
                "%(key)-35s: %(value)-30s" % dict(key=key, value=value)
            )

    except (ClientError, AssertionError):
        click.echo(
            "Stack `%s` does not exist." % name
        )


def _template(path):
    if not isinstance(path, Template):
        sys.path.append(os.getcwd())
        paths = path.split('.')

        path = __import__('.'.join(paths[:-1]))

        for attr in paths[1:]:
            path = getattr(path, attr)

    return path


@cli.command()
@click.argument('template', envvar='STACK_TEMPLATE')
def template(template):
    """ Show template as json.
    """
    template = _template(template)
    click.echo(template.to_json())


def manage(command):
    @click.option(
        '--template',
        '-t',
        envvar='STACK_TEMPLATE',
        required=True,
        help="Path to stack template.",
    )
    @click.option(
        '--parameter',
        '-p',
        type=(str, str),
        multiple=True,
        help="Stack parameter as `<key> <value>`.",
    )
    @click.option(
        '--iam',
        'capability',
        flag_value='CAPABILITY_IAM',
        help="Enable `CAPABILITY_IAM`.",
    )
    @click.option(
        '--named-iam',
        'capability',
        flag_value='CAPABILITY_NAMED_IAM',
        help="Enable `CAPABILITY_NAMED_IAM`.",
    )
    @click.option(
        '--tail',
        is_flag=True,
        help="Show stack events.",
    )
    @click.argument('name')
    @click.pass_obj
    def f(*args, **kwargs):
        tail = kwargs.pop('tail')
        command(*args, **kwargs)

        if tail:
            _events(args[0], kwargs['name'])

    return update_wrapper(f, command)


def update_params(template, params, previous):
    parameters = {
        key: None
        for key in template.parameters
    }
    parameters.update(
        {key: value for key, value in params},
    )

    params = []

    for key, value in parameters.items():
        if value is None and key not in previous:
            continue

        param = dict(
            ParameterKey=key,
            UsePreviousValue=(
                value is None and
                key in previous
            ),
        )

        if value is not None:
            param.update(dict(ParameterValue=value))

        params.append(param)

    return params


def stack_definition(client, template, name, parameter, capability):
    template = _template(template)

    try:
        previous_params = _parameters(client, name)

    except (ClientError, AssertionError):
        previous_params = dict()

    definition = dict(
        StackName=name,
        TemplateBody=template.to_json(indent=None),
        Parameters=update_params(template, parameter, previous_params),
    )

    if capability is not None:
        definition.update(dict(Capabilities=[capability]))

    return definition


@cli.command()
@manage
def create(client, *args, **kwargs):
    """ Create a new stack.
    """
    client.create_stack(**stack_definition(client, *args, **kwargs))


@cli.command()
@manage
def update(client, *args, **kwargs):
    """ Update an existing stack.
    """
    client.update_stack(**stack_definition(client, *args, **kwargs))


if __name__ == '__main__':
    cli.main()
