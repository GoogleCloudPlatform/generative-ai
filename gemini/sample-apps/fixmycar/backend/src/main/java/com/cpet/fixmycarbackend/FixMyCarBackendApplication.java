/*
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
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

  @Autowired
  private FixMyCarConfiguration config;

  // Set vector DB option based on user configuration
  @PostConstruct
  public void init() {
    // Ensure that Google Cloud Project ID is set
    String projectId = config.getProjectId();
    if (projectId == null || projectId.isEmpty()) {
      logger.error(
          "❌ application.properties value fixmycar.backend.projectId was unset or invalid. Please"
              + " set this value to your Google Cloud Project ID.");
      System.exit(1);
    }
    logger.info("🆔 Google Cloud Project ID set to: " + projectId);

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
