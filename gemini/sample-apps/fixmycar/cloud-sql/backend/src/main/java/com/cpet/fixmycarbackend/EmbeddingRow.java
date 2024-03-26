package com.cpet.fixmycarbackend;

import io.hypersistence.utils.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import java.util.List;
import org.hibernate.annotations.Type;

@Entity
@Table(name = "fixmycar")
public class EmbeddingRow {

  @Id
  @Column(name = "id")
  private String id;

  @Basic
  @Column(name = "text")
  private String text;

  // type list of doubles
  @Basic
  @Type(JsonType.class)
  @Column(name = "embedding", columnDefinition = "vector")
  private List<Double> embedding;

  public String getText() {
    return text;
  }
}
