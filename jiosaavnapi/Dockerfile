FROM python:3.8-alpine
WORKDIR /JioSaavnAPI
COPY . .
RUN apk update --no-cache && apk upgrade --no-cache
RUN pip3 install -r JioSaavnAPI/requirements.txt
EXPOSE 5000
CMD ["python3", "JioSaavnAPI/app.py"]
