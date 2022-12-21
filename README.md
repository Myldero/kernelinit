# `kernelinit`
A tool for automating setup of kernel pwn challenges.

## Installation
Clone the repo
```sh
git clone git@github.com:kalmarunionenctf/kernelinit.git
```
Install with pip
```
python3 -m pip install .
```

## Usage
Just run `kernelinit` in the directory of the challenge. It should hopefully automatically locate the relevant files to create the setup.

## Unintended solves
The tool may be able to find unintended solutions when the challenge author has let critical files or directories be writable to the user.
A list of tricks for these cases can be seen [here](tricks.md)