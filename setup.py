from setuptools import setup

install_requires = \
['python-libarchive~=4.2.1',
 'pexpect~=4.8.0',
 'vmlinux-to-elf @ git+https://github.com/marin-m/vmlinux-to-elf@3ff66e1']

package_data = {
    'kernelinit': [
        'templates/*',
        'templates/exploit-src/*',
    ]
}

setup(
    name='kernelinit',
    version='1.0.1',
    install_requires=install_requires,
    packages=['kernelinit'],
    entry_points = {
        'console_scripts': ['kernelinit=kernelinit.main:main']
    },
    package_data=package_data,
)
