FROM python:3.7-slim

RUN apt-get update && apt-get install -y openssh-server gcc
RUN mkdir /var/run/sshd
RUN ssh-keygen -t rsa -N "" -f /etc/ssh/key
RUN echo 'root:password' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

RUN apt-get update && apt-get install -y \
    libffi-dev \
    libssl-dev

RUN pip install \
    cryptography \
    bcrypt \
    pynacl \
    asyncssh \
    netifaces \
    scapy

CMD ["/usr/sbin/sshd", "-D", "-h", "/etc/ssh/key"]
WORKDIR /code
