Troposphere CLI
===============

Command line interface to manage troposphere CloudFormation stacks.


Installation
------------

pip install troposphere-cli


Usage
-----

.. code-block::

    Usage: trop [OPTIONS] COMMAND [ARGS]...

      Troposphere CLI.

    Options:
      -r, --region TEXT  The `AWS` region.  [required]
      --help             Show this message and exit.

    Commands:
      create      Create a new stack.
      events      Display stack events.
      list        List stacks.
      outputs     Show stack output values.
      parameters  Show templates parameter values.
      template    Show template as json.
      update      Update an existing stack.


Configuration
-------------

.. code-block::

    AWS_REGION=<aws_region>
    STACK_TEMPLATE=<path.to.template>
