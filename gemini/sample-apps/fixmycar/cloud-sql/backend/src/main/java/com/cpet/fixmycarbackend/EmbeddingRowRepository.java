package com.cpet.fixmycarbackend;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

// Source:
// https://stackoverflow.com/questions/76553746/what-jpa-hibernate-data-type-should-i-use-to-support-the-vector-extension-in-a
public interface EmbeddingRowRepository extends JpaRepository<EmbeddingRow, Long> {

  // Find nearest neighbors by a vector, for example value = "[1,2,3]"
  @Query(
      nativeQuery = true,
      value = "SELECT * FROM fixmycar ORDER BY embedding <-> cast(? as vector) LIMIT 3")
  List<EmbeddingRow> findNearestNeighbors(String value);
}
