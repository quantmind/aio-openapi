import os
from setuptools import setup, find_packages

import openapi


def read(name):
    filename = os.path.join(os.path.dirname(__file__), name)
    with open(filename) as fp:
        return fp.read()


def requirements(name):
    install_requires = []
    dependency_links = []

    for line in read(name).split('\n'):
        if line.startswith('-e '):
            link = line[3:].strip()
            if link == '.':
                continue
            dependency_links.append(link)
            line = link.split('=')[1]
        line = line.strip()
        if line:
            install_requires.append(line)

    return install_requires, dependency_links


meta = dict(
    version=openapi.__version__,
    description=openapi.__doc__,
    name="aio-openapi",
    packages=find_packages(exclude=["tests", "tests.*"]),
    long_description=read("readme.md"),
    long_description_content_type='text/markdown',
    license="BSD",
    maintainer_email='admin@lendingblock.com',
    url='https://github.com/lendingblock/aio-openapi',
    python_requires='>=3.6.0',
    install_requires=requirements('dev/requirements.txt'),
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Utilities'
    ],
    project_urls={
        'CI: circleci': 'https://circleci.com/gh/lendingblock/aio-openapi',
        'Coverage: codecov': 'https://codecov.io/gh/lendingblock/aio-openapi',
        'GitHub: issues': 'https://github.com/lendingblock/aio-openapi/issues',
        'GitHub: repo': 'https://github.com/lendingblock/aio-openapi',
    },
)


if __name__ == '__main__':
    setup(**meta)
