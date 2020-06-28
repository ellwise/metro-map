#FROM python:3.8
#LABEL maintainer "Elliott Wise <ell.wise@gmail.com>"
#COPY ./ /app
#WORKDIR "/app"
#RUN pip install -r /app/requirements.txt
#ENTRYPOINT ["python3"]
#CMD ["index.py"]

FROM python:3.7-slim AS build-env
COPY ./ /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt

FROM gcr.io/distroless/python3-debian10
LABEL maintainer "Elliott Wise <ell.wise@gmail.com>"
COPY --from=build-env /app /app
COPY --from=build-env /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
WORKDIR /app
ENV PYTHONPATH=/usr/local/lib/python3.7/site-packages
ENTRYPOINT ["python3"]
CMD ["index.py"]