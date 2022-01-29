FROM openjdk:11-jre-slim 

WORKDIR /lavalink 

COPY application.yml application.yml

RUN apt update -y && apt upgrade -y
RUN apt install wget -y
RUN wget https://github.com/freyacodes/Lavalink/releases/latest/download/lavalink.jar

EXPOSE 2333

CMD ["java", "-jar", "lavalink.jar"]
