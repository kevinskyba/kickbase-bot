from setuptools import setup

setup(
    name='Kickbase_Bot',
    version='0.0.3',
    packages=['kickbase_bot'],
    url='https://github.com/kevinskyba/kickbase-bot',
    license='MIT',
    author='kevinskyba',
    author_email='kevinskyba@live.de',
    description='Python bot framework for kickbase',
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    install_requires=(
        'requests',
    )
)
