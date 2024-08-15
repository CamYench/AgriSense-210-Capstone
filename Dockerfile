


# build container
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

# copy files
COPY . .

# install requirements
RUN pip3 install -r requirements.txt

# expose streamlit port
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "MVP_app_showcase.py", "--server.port=8501", "--server.address=0.0.0.0"]

