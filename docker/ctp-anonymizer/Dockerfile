# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM ubuntu:22.04

# Set the working directory to /app
WORKDIR /app

# Install openjdk-8-jdk, ant, git and make
RUN apt-get update && \
    apt-get purge openjdk-\* && \
    apt-get install -y openjdk-8-jdk ant git make && \
    rm -rf /var/lib/apt/lists/*

# Set to use Java 8 by default.
# Otherwise openjdk-11-jdk which is installed by ant is used by default.
# Method to set JAVA_HOME seems to work with ant but openjdk-11-jdk is still used
# by default when running java in the container.
# As a workaround we set the java executable to point to the java 8 executable.
# See https://docs.datastax.com/en/jdk-install/doc/jdk-install/installOpenJdkDeb.html
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
RUN update-alternatives --set java /usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java

# RUN git clone --recurse-submodules -b dev https://github.com/susom/mirc-ctp.git && \
#     cd mirc-ctp && \
#     make clean && make install && \
#     ant -v

# Clone and build CTP
RUN git clone https://github.com/johnperry/CTP.git && \
    cd CTP && \
    ant -v

# Clone and build DicomAnonymizerTool
# We need to fix the build.xml file to point to the proper CTP folder
RUN git clone https://github.com/johnperry/DicomAnonymizerTool.git && \
    cd DicomAnonymizerTool && \
    sed -i 's/\/Development\/CTP/\/app\/CTP/g' build.xml && \
    ant -v

# Make all jar file in folder and sub folders executable
RUN find /app -name "*.jar" -exec chmod +x {} \;

RUN apt-get remove -y ant git make && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create scripts folder for storing DicomAnonymizerTool scripts
# Fix also permissions in case the scripts folder is mounted from the host 
RUN mkdir -p scripts && chmod 775 scripts

# Copy the entrypoint script to /app
COPY docker/ctp-anonymizer/entrypoint_anonymizer.sh .

# Make the entrypoint script executable
RUN chmod +x entrypoint_anonymizer.sh

# Set the entrypoint to the entrypoint script running DicomAnonymizerTool
ENTRYPOINT ["/app/entrypoint_anonymizer.sh"]

# Define some build arguments for defining image metadata
ARG BUILD_DATE=today
ARG VCS_REF=unknown
ARG VERSION=1.0

# Define image metadata following label schema
# http://label-schema.org/rc1/
LABEL org.label-schema.build-date=${BUILD_DATE} \
    org.label-schema.schema-version="1.0" \
    org.label-schema.name="CTP DicomAnonymizerTool" \
    org.label-schema.description="CTP DicomAnonymizerTool is a command line tool for anonymizing DICOM files." \
    org.label-schema.url="https://translationalml.github.io/" \
    org.label-schema.vcs-ref=${VCS_REF} \
    org.label-schema.vcs-url="https://github.com/TranslationalML/tml-ctp" \
    org.label-schema.version=${VERSION} \
    org.label-schema.maintainer="The TranslationalML team" \
    org.label-schema.vendor="The TranslationalML team" \
    org.label-schema.docker.cmd="docker run --rm -u <user_id>:<group_id> -v <input_folder>:/input -v <output_folder>:/output -v <dat_script>:/scripts/da.script ctp-anonymizer:${VERSION} -in /input -out /output -da /scripts/da.script" \
    org.label-schema.docker.cmd.help="docker run -it --rm ctp-anonymizer:${VERSION} -h"
