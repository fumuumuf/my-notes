FROM ubuntu:16.04
ARG py_version="3.6.4"

# install utilities
RUN apt-get update && apt-get install -y sudo git wget zip gcc libatlas-base-dev \
    vim curl net-tools zsh make zlib1g-dev libssl-dev libreadline6-dev libbz2-dev libsqlite3-dev \
    language-pack-ja

RUN update-locale LANG=ja_JP.UTF-8
ENV LANG=ja_JP.UTF-8

RUN apt-get autoremove -y && apt-get clean

# pyenv
RUN git clone git://github.com/yyuu/pyenv.git .pyenv 
# ENV HOME /root
ENV PYENV_ROOT ${HOME}/.pyenv 
ENV PATH ${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}
RUN pyenv install ${py_version} &&  pyenv rehash && pyenv global ${py_version}

COPY requirements.txt requirements.txt 
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
