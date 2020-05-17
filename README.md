# api-manager-py

## Overview

Many APIs with rate limits push responsibility on API users to manage rate limiting, including those with SDKs.
`api-manager-py` is a Python library that aims to abstract away the complexity of managing rate limits,
allowing developers to focus on retrieving desired data without hacking together buggy, case-by-case solutions.
The API management functionality does not require using a specific library for interacting with an API, and will
automatically cache responses based on input parameters to reduce network IO. Simply implement a small API client
interface and start making requests.

## Installation

### Install from PyPi (preferred method)

```bash
pip install lc-api-manager
```

### Install from GitHub with Pip

```bash
pip install git+https://github.com/libcommon/api-manager-py.git@vx.x.x#egg=lc_api_manager
```

where `x.x.x` is the version you want to download.

## Install by Manual Download

To download the source distribution and/or wheel files, navigate to
`https://github.com/libcommon/api-manager-py/tree/releases/vx.x.x/dist`, where `x.x.x` is the version you want to install,
and download either via the UI or with a tool like wget. Then to install run:

```bash
pip install <downloaded file>
```

Do _not_ change the name of the file after downloading, as Pip requires a specific naming convention for installation files.

## Dependencies

`api-manager-py` depends on the [lc-cache](https://pypi.org/project/lc-cache/) for caching API responses. Only Python
versions >= 3.6 are officially supported.

## Getting Started

## Contributing/Suggestions

Contributions and suggestions are welcome! To make a feature request, report a bug, or otherwise comment on existing
functionality, please file an issue. For contributions please submit a PR, but make sure to lint, type-check, and test
your code before doing so. Thanks in advance!
