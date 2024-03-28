# FixMyCar Backend API (Java Spring)

### Testing locally

```bash
mvn clean compile
./mvnw spring-boot:run
```

### Testing the API with curl

Health check:

```
curl --location --request GET 'localhost:8080/health'
```

Test RAG:

```
curl --location 'localhost:8080/chat' \
--header 'Content-Type: application/json' \
--data '{
    "prompt": "What is the fuel capacity of a 2024 Cymbal Starlight?"
}'
```
