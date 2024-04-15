# Base image with Java 17 (using a lightweight Alpine variant for efficiency)
FROM eclipse-temurin:17-jdk-alpine as builder

# Set working directory
WORKDIR /workspace/app

# Copy Maven dependencies (for efficient caching and layer separation)
COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .
RUN ./mvnw dependency:go-offline -B

# Copy project source code
COPY src src

# Build the application with Maven
RUN ./mvnw package -DskipTests

# Create a lightweight runtime image
FROM eclipse-temurin:17-jdk-alpine

# Set working directory
WORKDIR /app

# Copy the built JAR file from the builder stage
COPY --from=builder /workspace/app/target/*.jar /app/app.jar

# Expose the application port (replace with your actual port if different)
EXPOSE 8080

# Run the application using Spring Boot's executable JAR
ENTRYPOINT ["java", "-jar", "/app/app.jar"]