
# Docstring Generator

This command-line tool helps to automatically generate, modify, or validate docstrings in Python files. It utilizes a GPT model for generating docstrings based on the function's code and context.

## Installation

Before using the tool, ensure that Python is installed on your system.

You will also need to have Ollama installed, and the ollama executable must be in the PATH in which the command is executed.

## Usage

The script is executed from the command line with several options to control its behavior. Here is the basic usage:


# pyluci.py Usage

Create, update, validate, or strip docstrings in Python files.

## Usage

```bash
usage: pyluci.py [-h] [-a [1-100]] [-c] [-d [1-100]] [-l {0,1,2}] [-m]
                 [-p] [-r] [-s] [-u] [-v] [--install-model MODEL_NAME]
                 [--list] [--model MODEL] [--host HOST] [--port PORT]
                 [filenames ...]
```

## Positional Arguments

- `filenames`  
  List of filenames to process. If an undecorated filename is provided, all functions in the file will be examined. To limit the scope of operations, filenames can be decorated by adding a colon-separated list of fully-qualified function names of the form `foo.bar.zoo`, where `foo`, `bar`, and `zoo` can be the names of functions or classes. Nesting of functions and classes is allowed. If a path is longer than the `--depth` field, a warning is reported and the function is not processed.

## Options

- `-h, --help`  
  Show this help message and exit.
- `-a [1-100], --attempts [1-100]`  
  Set the number of attempts for processing. Must be an integer in the range [1..100].
- `-c, --create`  
  Create new docstrings for functions that do not currently have one.
- `-d [1-100], --depth [1-100]`  
  Set the depth for processing. Must be an integer in the range [1..100].
- `-l {0,1,2}, --log-level {0,1,2}`  
  Set the log level. 0 = no logs, 1 = brief logs, 2 = verbose logs.
- `-m, --modify`  
  Modify the original files with new changes. If `-p` or `-r` is also specified, will prompt user before modifying the file.
- `-p, --preview`  
  Preview the content of the files without making changes unless `-m` is also specified, in which case it will prompt user before modifying the file.
- `-r, --report`  
  Show report after each file is processed. If the `-m` flag is present, this flag will cause the user to be prompted before the modification occurs.
- `-s, --strip`  
  Strip existing docstrings. When used in conjunction with `-v`, will only strip docstrings that fail validation. Incompatible with `-u` and `-c`.
- `-u, --update`  
  Update existing docstrings. If `-v` is specified, will only update if current docstring failed validation. Incompatible with `-s`.
- `-v, --validate`  
  Validate that the docstrings in the file correctly describe the source code. If `-u` is specified, update will only occur if validation fails. If `-s` is specified, docstring will be deleted if validation fails.
- `--install-model MODEL_NAME`  
  Install a model by name onto the Ollama server.
- `--list`  
  List all installed models available on the Ollama server.
- `--model MODEL`  
  Specify the model to operate on. Defaults to llama3.
- `--host HOST`  
  Specify the host of the Ollama server. Defaults to localhost.
- `--port PORT`  
  Specify the port of the Ollama server. Defaults to 11434.


### Examples

#### Common Use Cases

To create docstrings for all functions in `sample.py` that lack them. This example uses -c to create docstrings, -p to preview changes, and -m to modify the file with the results.

```
python pyluci.py -cpm sample.py
```

To update docstrings for all functions in `sample.py` that lack them. This example uses -u to update existing docstrings, -p to preview changes, and -m to modify the file with the results.

```
python pyluci.py -upm sample.py
```

To only update docstrings that are out of date, add the -v option:

```
python pyluci.py -upmv sample.py
```

Creation and updates can occur at the same time:

```
python pyluci.py -cupm sample.py
```

To produce a report on the correctness of existing docstrings, use the -v option without using -c or -u:

```
python pyluci.py -v sample.py
```

To remove docstrings from a file, use the -s option:

```
python pyluci.py --v sample.py
```

You can focus on a specific function or functions by appending a colon-separated list of fully-qualified function names to the file name. The following example will only validate docstrings in the function named 'function_name' at the module level, and the method named 'method_name' that is part of the class 'class_name' which is defined at the module level.

```
python pyluci.py -v sample.py:function_name:class_name.method_name
```

If you want to affect deeply-nested functions, you will need to increase the depth. By default, pyluci will only document top-level functions and methods of classes that are defined at the top level. Use -d to increase the depth:

```
python pyluci.py -v -d 2 sample.py:function_name.nest_function_name:class_name.nested_class_name.method_name
```


#### Managing Ollama

pyluci uses Ollama to manage the llama models used to generate docstrings. By default it uses llama3. Other models may be used by setting the --model option

```
python pyluci.py -cupm sample.py --model llama2
```

You can list available models with --list:

```
python pyluci.py --list
```

You can install a model with the --install-model option:


```
python pyluci.py --install-model llama2:latest
```

You can set the host and port of the ollama server with --host and --port:

```
python pyluci.py -cupm sample.py --host <some_hostname> --port <some_port>
```









