from setuptools import setup


with open('README.rst', 'r') as f:
    setup(
        name='troposphere-cli',
        version='0.1',
        description='Troposphere Command Line Interface',
        long_description=f.read(),
        author='jean-philippe serafin',
        author_email='tech@omixy.com',
        url='https://github.com/Omixy/troposphere-cli',
        packages=['trop'],
        install_requires=[
          'boto3',
          'click',
          'pytz',
          'troposphere',
        ],
        license='MIT',
        entry_points=dict(
            console_scripts=['trop=trop:cli.main'],
        ),
    )
