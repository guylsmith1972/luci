
# Docstring Generator

This command-line tool helps to automatically generate, modify, validate, or strip docstrings in Python files. It utilizes a GPT model for generating docstrings based on the function's code and comments.

## Installation

For Windows or WSL users, put dist/luci.exe in a location listed in your PATH environment variable. Standalone executables for other operating systems will be added in time.

You will also need to have [Ollama](https://ollama.com/download) installed, and the ollama executable must be in the PATH. Luci expects llama3 to be installed in Ollama by default. You can install in manually with 'ollama pull llama3' or you can use luci to install it with 'luci --install-model llama3'.


# Usage

Create, update, or validate docstrings in Python files.

```bash
usage: luci [-h] [-a [1-100]] [-c] [-d [1-100]] [-l {0,1,2}] [-m] [-p] [-r] [-s] [-u] [-v]
            [--install-model MODEL_NAME] [--list] [--model MODEL] [--host HOST] [--port PORT]
            [filenames ...]
```

## Positional Arguments

- `filenames`
  List of filenames to process. If an undecorated filename is provided, all functions in the
  file will be examined. To limit the scope of operations, filenames can be decorated by adding
  a colon-separated list of fully-qualified function names of the form `foo.bar.zoo`, where `foo`,
  `bar`, and `zoo` can be the names of functions or classes. Nesting of functions and classes is
  allowed. If a path is longer than the `--depth` field, a warning is reported, and the function
  is not processed.

## Options

- `-h, --help`
  Show this help message and exit.
- `-a [1-100], --attempts [1-100]`
  Set the number of attempts for processing. Must be an integer in the range [1-100].
- `-c, --create`
  Create new docstrings for functions that do not currently have one.
- `-d [1-100], --depth [1-100]`
  Set the depth for processing. Must be an integer in the range [1-100].
- `-l {0,1,2}, --log-level {0,1,2}`
  Set the log level. 0 = no logs, 1 = brief logs, 2 = verbose logs.
- `-m, --modify`
  Modify the original files with new changes. If -p or -r is also specified, the file will
  prompt the user before modifying.
- `-p, --preview`
  Preview the content of the files without making changes unless -m is also specified, in which
  case, it will prompt the user before modifying.
- `-r, --report`
  Show a report after each file is processed. If the -m flag is present, this flag will cause
  the user to be prompted before the modification occurs.
- `-s, --strip`
  Strip existing docstrings. When used in conjunction with -v, it will only strip docstrings
  that fail validation. Incompatible with -u and -c.
- `-u, --update`
  Update existing docstrings. If -v is specified, it will only update if the current docstring
  failed validation. Incompatible with -s.
- `-v, --validate`
  Validate that the docstrings in the file correctly describe the source code. If -u is
  specified, an update will only occur if validation fails. If -s is specified, the docstring
  will be deleted if validation fails.
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
luci -cpm sample.py
```

To update docstrings for all functions in `sample.py` that lack them. This example uses -u to update existing docstrings, -p to preview changes, and -m to modify the file with the results.

```
luci -upm sample.py
```

To only update docstrings that are out of date, add the -v option:

```
luci -upmv sample.py
```

Creation and updates can occur at the same time:

```
luci -cupm sample.py
```

To produce a report on the correctness of existing docstrings, use the -r and -v options without using -c or -u:

```
luci -vr sample.py
```

To remove docstrings from a file, use the -s option:

```
luci -ms sample.py
```

You can focus on a specific function or functions by appending a colon-separated list of fully-qualified function names to the file name. The following example will only validate docstrings in the function named 'function_name' at the module level, and the method named 'method_name' that is part of the class 'class_name' which is defined at the module level.

```
luci -vr sample.py:function_name:class_name.method_name
```

If you want to affect deeply-nested functions, you will need to increase the depth. By default, luci will only document top-level functions and methods of classes that are defined at the top level. Use -d to increase the depth:

```
luci -vr -d 2 sample.py:function_name.nested_function_name:class_name.nested_class_name.method_name
```


#### Managing Ollama

luci uses Ollama to manage the llama models used to generate docstrings. By default it uses llama3. Other models may be used by setting the --model option

```
luci -cupm sample.py --model llama2
```

You can list available models with --list:

```
luci --list
```

You can install a model with the --install-model option:


```
luci --install-model llama2:latest
```

You can set the host and port of the ollama server with --host and --port:

```
luci -cupm sample.py --host <some_hostname> --port <some_port>
```

### Roadmap

Future enhancements:
1. Add options to provide alternative sample docstrings 
1. Extend to support additional programming languages
1. Improve formatting of docstrings
1. Add change history to docstring or in comments following docstring
