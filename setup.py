from setuptools import setup, find_packages

import openapi


meta = dict(
    version=openapi.__version__,
    description=openapi.__doc__,
    name='aio-openapi',
    packages=find_packages(exclude=['tests']),
    license='BSD'
)


if __name__ == '__main__':
    setup(**meta)
