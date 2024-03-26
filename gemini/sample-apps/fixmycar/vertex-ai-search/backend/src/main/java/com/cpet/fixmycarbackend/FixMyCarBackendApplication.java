package com.cpet.fixmycarbackend;

import javax.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication()
public class FixMyCarBackendApplication {
  private static final Logger logger = LoggerFactory.getLogger(FixMyCarBackendController.class);

  @Autowired private FixMyCarConfiguration config;

  // Set vector DB option based on user configuration
  @PostConstruct
  public void init() {
    // Ensure that GCP Project ID is set
    String projectId = config.getProjectId();
    if (projectId == null || projectId.isEmpty()) {
      logger.error(
          "❌ application.properties value fixmycar.backend.projectId was unset or invalid. Please"
              + " set this value to your GCP Project ID.");
      System.exit(1);
    }
    logger.info("🆔 GCP Project ID set to: " + projectId);

    String vertexDataStoreId = config.getVertexDataStoreId();
    // if set, log it
    if (vertexDataStoreId != null && !vertexDataStoreId.isEmpty()) {
      logger.info("🗃️ Vertex Datastore ID set to: " + vertexDataStoreId);
    }
  }

  public static void main(String[] args) {
    logger.info("⭐ Starting server with grounding data store: Vertex AI Search");
    SpringApplication.run(FixMyCarBackendApplication.class, args);
  }
}
