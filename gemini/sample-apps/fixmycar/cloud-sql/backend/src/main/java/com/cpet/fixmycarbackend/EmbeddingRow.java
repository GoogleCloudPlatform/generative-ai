package com.cpet.fixmycarbackend;

import jakarta.persistence.*;

import org.hibernate.annotations.Type;
import io.hypersistence.utils.hibernate.type.json.JsonType;
import java.util.List;

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