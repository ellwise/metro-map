FROM python:3.7-slim AS build-env
COPY ./ /home/project/dash_app
WORKDIR /home/project/dash_app
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r ./requirements.txt

# this disto runs python 3.7, others use older versions...
FROM gcr.io/distroless/python3-debian10
LABEL maintainer "Elliott Wise <ell.wise@gmail.com>"
COPY --from=build-env /home/project/dash_app /home/project/dash_app
COPY --from=build-env /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages
# next line is gunicorn
COPY --from=build-env /usr/local/bin /usr/local/bin
WORKDIR /home/project/dash_app
ENV PYTHONPATH=/usr/local/lib/python3.7/site-packages
#ENTRYPOINT ["python3"]
#CMD ["index.py"]