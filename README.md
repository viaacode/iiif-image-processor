# iiif-image-processor

## Synopsis

A service that transforms images using Kakadu using specific settings based on the type that the image represents.
The service watches a folder for incoming images and places the transformed image in a location based on the image's metadata.

## Prerequisites

* Git
* Docker (optional)
* Python 3.10+
* Access to the meemoo PyPi
* Access to a licensed Kakadu

## Usage

1. Clone this repository with:

    `$ git clone https://github.com/viaacode/iiif-image-processor.git`

2. Change into the new directory:

    `$ cd iiif-image-processor`

3. Set the needed config:

Included in this repository is a config.yml file detailing the required configuration. There is also an .env.example file containing all the needed env variables used in the config.yml file. All values in the config have to be set in order for the application to function correctly. You can use !ENV ${EXAMPLE} as a config value to make the application get the EXAMPLE environment variable.

### Running locally

1. Start by creating a virtual environment:

    `$ python -m venv venv`

2. Activate the virtual environment:

    `$ source venv/bin/activate`

3. Install the external modules:

    ```
    $ pip install -r requirements.txt \
        --extra-index-url http://do-prd-mvn-01.do.viaa.be:8081/repository/pypi-all/simple \
        --trusted-host do-prd-mvn-01.do.viaa.be && \
      pip install -r requirements-dev.txt
    ```
4. Make sure Kakadu is available on the system:
    `$ kdu_compress`
    If this command does not succeed, please install Kakadu (https://kakadusoftware.com/)

5. Make sure to load in the ENV vars.

6. Run the tests with:

    `$ python -m pytest -v --cov=./app`

7. Run the application:

    `$ python -m main`

### Running using Docker

Kakadu is installed as part of the Docker build process. Access to the meemoo-repository is needed.

1. Build the container:

    `$ docker build -t iiif-image-processor .`

2. Run the tests in a container:

    `$ docker run --env-file .env.example --rm --entrypoint python iiif-image-processor:latest -m pytest -v --cov=./app`

3. Run the container (with specified `.env` file):

    `$ docker run --env-file .env -v ~/folder_to_watch:/export/home/viaa/pub -v ~/processing_folder:/opt/image-processing-workfolder -v ~/results:/export/images/ iiif-image-processor:latest`
