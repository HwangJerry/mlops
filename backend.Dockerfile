FROM localhost:30445/ghkdwp018/mlops-app-base:latest

WORKDIR /mlops

COPY ./app /mlops/app

RUN mkdir -p /mlops/models/t5-small

ENTRYPOINT ["uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]