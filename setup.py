from distutils.core import setup
from setuptools import find_packages

exec(open('thunderfish/version.py').read())

setup(name='thunderfish',
      version=__version__,
      packages=find_packages(exclude=['contrib', 'doc', 'tests*']),
      entry_points={
        'console_scripts': [
            'thunderfish = thunderfish.thunderfish:main',
            'fishfinder = thunderfish.fishfinder:main',
            'tracker = thunderfish.tracker:main',
        ]},
      description='Algorithms and scripts for analyzing recordings of e-fish electric fields.',
      author='Jan Benda, Juan F. Sehuanes, Till Raab, Joerg Henninger, Jan Grewe, Fabian Sinz',
      requires=['numpy', 'matplotlib', 'audioio']
      )
