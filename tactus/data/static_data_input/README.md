# Introduction

The checker tool is used to verify that the input static data files are present on the machine.

A set of json file containing a list of data files for each cycle.

These json files are generated using checker.py, by providing a folder containing the reference data files. This is done on ATOS.
The json file can then be used to check that all the files are present and have a correct size on another machine.

# Usage

1. Generate a reference json file on ATOS

```
python checker.py --generate  --folder /hpcperm/snh02/DEODE --json cy49t2/reference.json
```

2. Check the content of a folder against a reference file

This is an example for Leonardo:
```
python checker.py --folder /leonardo_work/DestE_330_26/users/SAN/static/DEODE --json reference.json
```

## Verbose mode

The '--verbose' argument activates detailed output.
```
python checker.py --validate --folder /leonardo_work/DestE_330_26/users/SAN/static/DEODE --json reference.json --verbose

```
## Ignore files and green files

You can provide:
- a `ignore` file to filter files and folders, in the same way as you would use a `.gitignore` file in git.
- a `green` file to specify which files are accepted 

Example:

Atos:
```
python checker.py --generate --folder /hpcperm/snh02/DEODE --json cy49t2/reference.json --ignore cy49t2/.ignore --green cy49t2/.green
```

Leonardo:

```
python checker.py --folder /leonardo_work/DestE_330_26/users/SAN/static/DEODE --json cy49t2/reference.json --green cy49t2/.green

```

## Command output: --cmd, --scp_host and --force_update


You can generate the commands to copy the missing and outdated files using the `--cmd` optional argument:

Example: generate the cp commands to copy locally data into a new local folder `~/temp` on ATOS:
```
python checker.py  --folder ~/tmp --json cy49t2/reference.json --cmd
```

You can generate scp instructions to copy data from a remote host, by provide the `scp_host` in addition to `--cmd`


Example: generate the scp commands to retrieve data from ATOS on Leonardo:
```
python checker.py --folder /leonardo_work/DestE_330_26/users/SAN/static/DEODE --json cy49t2/reference.json --cmd --scp_host hpc-login
```

By default, no instruction will be generated for the data that are already present in the --folder directory but have an inconsistent size in comparison to the one provided in the reference json file.
You can generate the commands to override those files by providing the `--force_update` flag:

Example: generate the scp commands to retrieve data from ATOS on Leonardo and override the existing files:

```
python checker.py --folder /leonardo_work/DestE_330_26/users/SAN/static/DEODE --json cy49t2/reference.json --cmd --scp_host hpc-login --force_update
```

## Helper bash scripts

Some helper bash scripts are provided, in order to help you regenerating the reference json files, the green file and create a new folder from the reference file.
