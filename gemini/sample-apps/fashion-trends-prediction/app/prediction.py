"""Predicts fashion trends based on a given dataset.

This module uses a combination of UMAP, HDBSCAN, and BERTopic to generate predictions.

Classes:
    Prediction: Predicts fashion trends based on a given dataset.
"""

# pylint: disable=E0401

from typing import List, Tuple

from bertopic import BERTopic
from hdbscan import HDBSCAN
from umap import UMAP


class Prediction:
    """Predicts fashion trends based on a given dataset.

    This class uses a combination of UMAP, HDBSCAN, and BERTopic to generate predictions.

    Attributes:
        data (dict): A dictionary containing the data to be used for prediction.
        umap_model (UMAP): A UMAP model used for dimensionality reduction.
        hdbscan_model (HDBSCAN): A HDBSCAN model used for clustering.
        model_a (BERTopic): A BERTopic model used for topic modeling.
    """

    def __init__(self, data: dict):
        """Initializes the Prediction class.

        Args:
            data (dict): A dictionary containing the data to be used for prediction.
        """
        self.data = data
        self.umap_model = UMAP(
            n_neighbors=5, n_components=5, min_dist=0.05, metric="cosine"
        )
        self.hdbscan_model = HDBSCAN(
            min_cluster_size=10,
            min_samples=10,
            gen_min_span_tree=True,
            prediction_data=True,
        )

        self.model_a = BERTopic(
            umap_model=self.umap_model,
            hdbscan_model=self.hdbscan_model,
            top_n_words=5,
            language="english",
            calculate_probabilities=True,
            verbose=True,
            n_gram_range=(1, 5),
        )

    def query(self, category: str, country: str) -> Tuple[List[str], List[List[str]]]:
        """Queries the model to generate predictions.

        Args:
            category (str): The category of the data to be used for prediction.
            country (str): The country of the data to be used for prediction.

        Returns:
            list: A list of cluster representatives.
            list: A list of additional documents.
        """
        text = [
            item
            for item in self.data["finaldata"][country][category]
            if isinstance(item, str)
        ]

        try:
            _ = self.model_a.fit_transform(text)
        except TypeError:
            num_elements = len(text)
            if num_elements < 25:
                mul = (25 - num_elements) // num_elements + 1
                text += text * mul
                _ = self.model_a.fit_transform(text)

        freq = self.model_a.get_topic_info()
        n = min(5, len(freq))
        df = self.model_a.get_document_info(text)

        cluster_representatives = []
        additional_docs = []

        total_topics = 0
        for _, row in freq.iterrows():
            topic = row["Topic"]

            if topic == -1:
                continue

            if total_topics >= n:
                break

            cluster = df[df["Topic"] == topic]
            cluster_repr_doc = cluster[cluster["Representative_document"]][
                "Document"
            ].iloc[0]

            if cluster_repr_doc in cluster_representatives:
                continue

            total_topics += 1
            sorted_cluster = cluster.sort_values(by="Probability", ascending=False)
            docs_set = set()
            docs_set.add(cluster_repr_doc)
            for _, row in sorted_cluster.iterrows():
                if len(docs_set) == 4:
                    break
                docs_set.add(row["Document"])

            docs_set.remove(cluster_repr_doc)

            cluster_representatives.append(cluster_repr_doc)
            additional_docs.append(list(docs_set))

        return cluster_representatives, additional_docs
