from setuptools import setup, find_packages

setup(
    name='3dsconv',
    version='4.2',
    url='https://github.com/ihaveamac/3dsconv',
    author='Ian',
    license='MIT',
    description='Converts Nintendo 3DS CTR Cart Image files (CCI, ".cci", ".3ds") to the CTR Importable Archive format (CIA)',
    install_requires=['pyaes'],
    packages=find_packages(),
    py_modules=['wrapper'],
    entry_points={'console_scripts': ['3dsconv=wrapper:main']},
)
