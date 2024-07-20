# load python image
FROM python:3.11-slim

# set the working directory in the container
WORKDIR /app
RUN mkdir /app/downloads

# copy the dependencies file to the working directory
COPY . .

# upgrade
RUN apt-get update -y && \
    apt-get upgrade -y 
    # apt install -y wget unzip curl jq

RUN apt install ca-certificates fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libgcc1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 lsb-release wget xdg-utils -y

# RUN python
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "download.py"]