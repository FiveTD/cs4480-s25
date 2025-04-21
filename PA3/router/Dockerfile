FROM ubuntu

RUN apt-get update
RUN apt-get -y install bash iproute2 net-tools tcpdump vim iputils-ping
RUN apt-get clean

# Install FRR
# apt -y install curl; apt -y install gnupg; curl -s https://deb.frrouting.org/frr/keys.gpg | tee /usr/share/keyrings/frrouting.gpg > /dev/null; apt install lsb-release; FRRVER="frr-stable"; echo deb '[signed-by=/usr/share/keyrings/frrouting.gpg]' https://deb.frrouting.org/frr $(lsb_release -s -c) $FRRVER | tee -a /etc/apt/sources.list.d/frr.list; apt update; apt -y install frr frr-pythontools
RUN apt -y install curl
RUN apt -y install gnupg
RUN curl -s https://deb.frrouting.org/frr/keys.gpg | tee /usr/share/keyrings/frrouting.gpg > /dev/null
RUN apt -y install lsb-release
ENV FRRVER="frr-stable"
RUN echo deb '[signed-by=/usr/share/keyrings/frrouting.gpg]' https://deb.frrouting.org/frr $(lsb_release -s -c) $FRRVER | tee -a /etc/apt/sources.list.d/frr.list
RUN apt update; apt -y install frr frr-pythontools

COPY startdaemon.sh /
RUN chmod +x /startdaemon.sh

CMD ["bash"]