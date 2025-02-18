FROM openfaas/of-watchdog:0.7.2 as watchdog

# FROM python:3.8-slim-buster
# FROM nvidia/cuda:11.0-cudnn8-devel-ubuntu18.04
FROM nvidia/cuda:11.0-cudnn8-runtime-ubuntu18.04
ENV PATH /opt/conda/bin:$PATH

RUN apt-get update --fix-missing && \
    apt-get install -y wget bzip2 ca-certificates curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -tipsy && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc

ENV PATH /opt/conda/bin:$PATH

ENV LD_LIBRARY_PATH /usr/local/cuda-11.0/lib64:/usr/local/cuda-11.0/extras/CUPTI/lib64:/usr/local/cuda-11.0/targets/x86_64-linux/lib:/usr/local/nvidia/lib64:$LD_LIBRARY_PATH

USER root

COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog
RUN chmod +x /usr/bin/fwatchdog

RUN mkdir -p /usr/share/man/man1 /usr/share/man/man2
RUN apt-get update \
    && apt-get install -y curl openjdk-11-jre ca-certificates \
    && rm -rf /var/lib/apt/lists/

# Add non root user
RUN groupadd app && useradd -r -g app app

WORKDIR /home/app/

RUN chown -R app /home/app

USER app

# install and setup node
ENV NODE_VERSION=12.6.0
ENV NVM_DIR=/home/app/.nvm
RUN mkdir -p $NVM_DIR
RUN curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash  
RUN . "$NVM_DIR/nvm.sh" && nvm install ${NODE_VERSION}   
RUN . "$NVM_DIR/nvm.sh" && nvm use v${NODE_VERSION}  
RUN . "$NVM_DIR/nvm.sh" && nvm alias default v${NODE_VERSION}    
ENV PATH="${NVM_DIR}/versions/node/v${NODE_VERSION}/bin/:${PATH}"

USER root

# WORKDIR /home/app/

COPY java-service /home/app/java-service
COPY python-service /home/app/python-service
COPY node-service /home/app/node-service


WORKDIR /home/app/node-service/

RUN npm i

WORKDIR /home/app/

RUN chown -R app /home/app && \
    mkdir -p /home/app/python && chown -R app /home/app
USER app
ENV PATH=$PATH:/home/app/.local/bin:/home/app/python/bin/
ENV PYTHONPATH=$PYTHONPATH:/home/app/python:/home/app/function

RUN pip install -r python-service/requirements.txt --target=/home/app/python