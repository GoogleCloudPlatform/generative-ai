package com.cpet.fixmycarbackend;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "fixmycar.backend")
public class FixMyCarConfiguration {
  private String projectId;

  public String getProjectId() {
    return projectId;
  }

  public void setProjectId(String myprojectid) {
    this.projectId = myprojectid;
  }
}
