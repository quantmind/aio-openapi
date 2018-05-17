import os


if not os.environ.get('PYTHON_ENV'):
    os.environ['PYTHON_ENV'] = 'test'
