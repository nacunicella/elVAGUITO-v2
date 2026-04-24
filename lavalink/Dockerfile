FROM eclipse-temurin:21-jre-jammy

WORKDIR /opt/lavalink

# Copiar el jar y la configuración
COPY Lavalink.jar Lavalink.jar
COPY application.yml application.yml

# Exponer el puerto
EXPOSE 2333

# Comando para arrancar
ENTRYPOINT ["java", "-jar", "Lavalink.jar"]
