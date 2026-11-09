from setuptools import find_packages
from setuptools import setup

setup(
  name='crane_x7_description',
  version='4.0.0',
  packages=find_packages(
      include=('crane_x7_description', 'crane_x7_description.*')),
)
