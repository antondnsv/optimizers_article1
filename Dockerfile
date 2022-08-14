FROM python:3.8-slim

ENV TOOL_DIR /opt
ENV AM_I_IN_A_DOCKER_CONTAINER Yes
ENV PATH="${PATH}:${TOOL_DIR}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential \
                                              git \
                                              gfortran \
                                              file \
                                              wget \
                                              unzip \
                                              zlib1g-dev \
                                              bison \
                                              flex \
                                              libgmp-dev \
                                              libreadline-dev \
                                              libncurses5-dev \
                                              glpk-utils \
                                              libblas-dev \
                                              liblapack-dev && \
    rm -rf /var/lib/apt/lists/*

# Install IpOPT
WORKDIR ${TOOL_DIR}
RUN wget https://ampl.com/dl/open/ipopt/ipopt-linux64.zip && \
    unzip ipopt-linux64.zip -d ${TOOL_DIR} && \
    rm -f ${TOOL_DIR}/coin-license.txt && \
    rm ipopt-linux64.zip

# Install CBC
WORKDIR ${TOOL_DIR}
RUN wget https://ampl.com/dl/open/cbc/cbc-linux64.zip && \
    unzip cbc-linux64.zip -d ${TOOL_DIR} && \
    rm -f ${TOOL_DIR}/coin-license.txt && \
    rm cbc-linux64.zip

# Install cvxopt
RUN git clone https://github.com/cvxopt/cvxopt.git && \
    cd cvxopt && \
    git checkout `git describe --abbrev=0 --tags` && \
    export CVXOPT_BUILD_DSDP=1    # optional && \
    export CVXOPT_BUILD_FFTW=1    # optional && \
    export CVXOPT_BUILD_GLPK=1    # optional && \
    export CVXOPT_BUILD_GSL=1     # optional && \
    python setup.py install


WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["bash"]
