.. _installation:

***********************************
Installation Instructions
***********************************


Prerequisites
==============

To use TML-CTP, the following tools must be installed on your system:

1. **Docker**: Docker is required as it serves as the containerization engine for TML-CTP. Ensure Docker is installed and configured correctly on your system. 
   For installation guidance, please visit the `Docker Installation Guide <https://docs.docker.com/get-docker/>`_.

2. **Python 3.10 with pip**: Python 3.10 and the pip package installer are necessary for managing dependencies and running the software.
   Make sure Python 3.10 is installed on your system along with pip.

3. **Make** (Optional, only for manual installation): 
   If you plan to perform a manual installation, you will need to install `make`, a build automation tool. 
   Make simplifies the execution of various tasks related to the project, particularly in the context of manual installation and development workflows.
   Refer to the `Make Official Documentation <https://www.gnu.org/software/make/>`_ for installation instructions.

.. note::
   **Important**: `make` is primarily a build automation tool available on Unix-like systems, including Linux and macOS. It is not natively available on Windows.
   However, Windows users can access `make` by using the Windows Subsystem for Linux (WSL) or by installing it through other tools like Cygwin or MinGW. WSL is the easiest way to get `make` running on Windows. 
   For more details, refer to the `WSL Installation Guide <https://docs.microsoft.com/en-us/windows/wsl/install>`_.

Installation
============

There are two ways to install TML-CTP:

1. **Using Container Technologies (RECOMMENDED)**
2. **Within a Manually Prepared Environment (Manual Installation)** 

Containerized Execution (Docker)
--------------------------------

The easiest and recommended way to install and run TML-CTP is by using Docker. This method simplifies the setup process and ensures consistency across different environments. The installation involves two main steps:

1. **Pull the TML-CTP Anonymizer Docker Image**: 

   To get started, pull the Docker image for TML-CTP from `quay.io`:

   .. code-block:: bash

       docker pull quay.io/translationalml/tml-ctp-anonymizer:1.0.0

2. **Install the TML-CTP Python Package**:

   In a Python 3.10 environment, install the `tml_ctp` package using pip:

   .. code-block:: bash

       pip install tml_ctp==1.0.0

   This will install the main `tml_ctp_dat_batcher` script, along with two utility scripts: `tml_ctp_clean_series_tags` and `tml_ctp_delete_identifiable_dicoms`, as well as all necessary Python dependencies.

Once these steps are completed, you’re all set to use TML-CTP with Docker!

Manual Installation (Python 3.10+)
--------------------------------------------

For users who prefer or require a manual installation, TML-CTP can be installed within a manually prepared Python environment. The manual installation consists of five main steps:

1. **Clone the Repository Locally**:

   First, clone the TML-CTP repository to your local machine:

   .. code-block:: bash

       cd <preferred-installation-directory>
       git clone git@github.com:TranslationalML/tml-ctp.git
       cd tml-ctp

2. **Build the Docker Image**:

   After cloning the repository, build the Docker image using `make`:

   .. code-block:: bash

       make build-docker

3. **Create a Python Virtual Environment**:

   Next, create a Python virtual environment to isolate the TML-CTP dependencies from other projects on your system:

   .. code-block:: bash

       python3.10 -m venv venv

4. **Activate the Python Virtual Environment**:

   Activate the virtual environment to start using it:

   - On Linux and macOS:

     .. code-block:: bash

        source venv/bin/activate

   - On Windows:

     .. code-block:: bash

        venv\Scripts\activate

5. **Install the Python Development Environment**:

   Finally, install all the necessary Python dependencies and the TML-CTP package using `make`:

   .. code-block:: bash

       make install-python-all

   This command will install:

   - All Python dependencies required for development (e.g., `black` for code formatting and `pytest` for testing).
   - The `tml_ctp` package, including the `tml_ctp_dat_batcher` script and other utility scripts.
   - All dependencies required by the `tml_ctp` package.

By following these steps, you will have a fully prepared environment for developing and running TML-CTP.