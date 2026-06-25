FROM python:3.12-slim

WORKDIR /app

COPY . .
RUN ln -snf /usr/local/bin/python /usr/bin/python3
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r service-desk-agent/scripts/requirements.txt

# Build every board (deps + pre-rendered data). Boards are listed in build.sh —
# add a board there, this Dockerfile never changes.
RUN bash build.sh

WORKDIR /app/service-desk-agent

EXPOSE 8080

CMD ["python3", "scripts/main.py"]
