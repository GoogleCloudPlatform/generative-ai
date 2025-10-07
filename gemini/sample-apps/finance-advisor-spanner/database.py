"""This file is for database operations done by the application"""

# pylint: disable=line-too-long
import os

from dotenv import load_dotenv
from google.api_core.client_options import ClientOptions
from google.cloud import spanner
import pandas as pd
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

load_dotenv()

instance_id = os.getenv("instance_id")
database_id = os.getenv("database_id")
api_endpoint = os.getenv("api_endpoint")

options = ClientOptions(api_endpoint=api_endpoint)
spanner_client = spanner.Client(client_options=options)

instance = spanner_client.instance(instance_id)
database = instance.database(database_id)


def spanner_read_data(query: str, *vector_input: list) -> pd.DataFrame:
    """This function helps read data from Spanner"""
    with database.snapshot() as snapshot:
        if len(vector_input) != 0:
            results = snapshot.execute_sql(
                query,
                params={"vector": vector_input[0]},
            )
        else:
            results = snapshot.execute_sql(query)
        rows = list(results)
        cols = [x.name for x in results.fields]
        return pd.DataFrame(rows, columns=cols)


def fts_query(query_params: list) -> dict:
    """This function runs Full Text Search Query"""
    if query_params[1] == "":
        fts_query_str = (
            "SELECT DISTINCT fund_name,investment_strategy,investment_managers,fund_trailing_return_ytd,top5_holdings FROM EU_MutualFunds WHERE SEARCH(investment_strategy_Tokens, '"
            + query_params[0]
            + "') order by fund_name;"
        )
    else:
        fts_query_str = (
            "SELECT DISTINCT fund_name, manager, strategy, score FROM (SELECT fund_name , investment_managers AS manager, investment_strategy as strategy, SCORE_NGRAMS(investment_managers_Substring_Tokens_NGRAM, '"
            + query_params[1]
            + "') AS score FROM EU_MutualFunds WHERE SEARCH_NGRAMS(investment_managers_Substring_Tokens_NGRAM, '"
            + query_params[1]
            + "', min_ngrams=>1) AND SEARCH(investment_strategy_Tokens, '"
            + query_params[0]
            + "') ) ORDER BY score DESC;"
        )

    return_vals = {}
    return_vals["query"] = fts_query_str
    df = spanner_read_data(fts_query_str)

    return_vals["data"] = df
    return return_vals


def semantic_query(query_params: list) -> dict:
    """This function runs Semantic Text Search Query"""
    if query_params[1].strip() != "":
        semantic_query_string = (
            "SELECT fund_name, investment_strategy,investment_managers, COSINE_DISTANCE( investment_strategy_Embedding, (SELECT embeddings. VALUES FROM ML.PREDICT( MODEL EmbeddingsModel, (SELECT '"
            + query_params[0]
            + "' AS content) ) ) ) AS distance FROM EU_MutualFunds WHERE investment_strategy_Embedding is not NULL  AND  search_substring(investment_managers_substring_tokens, '"
            + query_params[1]
            + "')ORDER BY distance LIMIT 10;"
        )
    else:
        semantic_query_string = (
            "SELECT fund_name, investment_strategy,investment_managers, COSINE_DISTANCE( investment_strategy_Embedding, (SELECT embeddings. VALUES FROM ML.PREDICT( MODEL EmbeddingsModel, (SELECT '"
            + query_params[0]
            + "' AS content) ) ) ) AS distance FROM EU_MutualFunds WHERE investment_strategy_Embedding is not NULL  ORDER BY distance LIMIT 10;"
        )
    return_vals = {}
    return_vals["query"] = semantic_query_string
    df = spanner_read_data(semantic_query_string)

    return_vals["data"] = df
    return return_vals


def semantic_query_ann(query_params: list) -> dict:
    """This function runs Semantic Text Search ANN Query"""

    embedding_query = (
        'SELECT embeddings. VALUES as vector FROM ML.PREDICT( MODEL EmbeddingsModel, (SELECT "'
        + query_params[0]
        + '" AS content) ) ;'
    )
    vector_input = spanner_read_data(embedding_query).values.tolist()

    if query_params[1].strip() != "":
        ann_query = (
            "SELECT funds.fund_name, funds.investment_strategy, funds.investment_managers FROM (SELECT NewMFSequence, APPROX_EUCLIDEAN_DISTANCE(investment_strategy_Embedding_vector, @vector, options => JSON '{\"num_leaves_to_search\": 10}') AS distance FROM EU_MutualFunds @{force_index = InvestmentStrategyEmbeddingIndex} WHERE investment_strategy_Embedding_vector IS NOT NULL ORDER BY distance LIMIT 500 ) AS ann JOIN EU_MutualFunds AS funds ON ann.NewMFSequence = funds.NewMFSequence WHERE SEARCH_NGRAMS(funds.investment_managers_Substring_Tokens_NGRAM, '"
            + query_params[1]
            + "',min_ngrams=>1)  ORDER BY SCORE_NGRAMS(funds.investment_managers_Substring_Tokens_NGRAM, '"
            + query_params[1]
            + "') desc;"
        )
    else:
        ann_query = "SELECT fund_name, investment_strategy, investment_managers, APPROX_EUCLIDEAN_DISTANCE(investment_strategy_Embedding_vector, @vector, options => JSON '{\"num_leaves_to_search\": 10}') AS distance FROM EU_MutualFunds @{force_index = InvestmentStrategyEmbeddingIndex} WHERE investment_strategy_Embedding_vector IS NOT NULL ORDER BY distance LIMIT 100;"
    results_df = spanner_read_data(ann_query, vector_input[0][0])
    results_df = spanner_read_data(ann_query, vector_input[0][0])
    results_df = spanner_read_data(ann_query, vector_input[0][0])
    results_df = spanner_read_data(ann_query, vector_input[0][0])

    return_vals = {}
    return_vals["query"] = ann_query
    return_vals["data"] = results_df
    return return_vals


def like_query(query_params: list) -> dict:
    """This function runs Precise Text Search Query"""

    if query_params[1] == "EXCLUDE":
        query_params[1] = "AND"
    precise_query = (
        " SELECT DISTINCT fund_name, investment_managers, investment_strategy FROM EU_MutualFunds WHERE investment_managers LIKE ('%"
        + query_params[3]
        + "%') AND ( investment_strategy LIKE ('%"
        + query_params[0]
        + "%') "
        + query_params[1]
        + " investment_strategy LIKE ('%"
        + query_params[2]
        + "%') ) ORDER BY fund_name;"
    )
    return_vals = {}
    return_vals["query"] = precise_query
    df = spanner_read_data(precise_query)

    return_vals["data"] = df
    return return_vals


def compliance_query(query_params: list) -> dict:
    """This function runs Compliance Graph  Search Query"""
    graph_compliance_query = (
        "GRAPH FundGraph MATCH (sector:Sector {sector_name: '"
        + query_params[0]
        + "'})<-[:BELONGS_TO]-(company:Company)<-[h:HOLDS]-(fund:Fund) RETURN fund.fund_name, SUM(h.percentage) AS totalHoldings GROUP BY fund.fund_name NEXT FILTER totalHoldings > "
        + query_params[1]
        + " RETURN fund_name, totalHoldings"
    )

    return_vals = {}
    return_vals["query"] = graph_compliance_query
    df = spanner_read_data(graph_compliance_query)
    return_vals["data"] = df
    return return_vals


def graph_dtls_query() -> dict:
    """This function runs Graph Details  Query"""
    company_query = "select CompanySeq,name from  Companies;"

    return_vals = {}
    df_companies = spanner_read_data(company_query)
    return_vals["Companies"] = df_companies

    sector_query = "select * from  Sectors;"
    df_sectors = spanner_read_data(sector_query)
    return_vals["Sectors"] = df_sectors

    managers_query = "select * from  Managers LIMIT 100;"
    df_managers = spanner_read_data(managers_query)
    return_vals["Managers"] = df_managers

    company_belong_sector_query = "SELECT * from CompanyBelongsSector;"
    df_comp_sec_edge = spanner_read_data(company_belong_sector_query)
    return_vals["CompanySectorRelation"] = df_comp_sec_edge

    mgr_fund_edge_query = " SELECT mgrs.NewMFSequence,fund_name,ManagerSeq from ManagerManagesFund mgrs JOIN EU_MutualFunds funds ON mgrs.NewMFSequence =  funds.NewMFSequence where ManagerSeq in (select ManagerSeq from Managers LIMIT 100);"
    mgr_fund_edge = spanner_read_data(mgr_fund_edge_query)
    return_vals["ManagerFundRelation"] = mgr_fund_edge

    funds_node_query = "select fund_name, NewMFSequence from EU_MutualFunds where NewMFSequence in (SELECT NewMFSequence FROM FundHoldsCompany);"
    funds_node = spanner_read_data(funds_node_query)
    return_vals["Funds"] = funds_node

    funds_hold_company_edge_query = "SELECT * FROM FundHoldsCompany;"
    funds_hold_company_edge = spanner_read_data(funds_hold_company_edge_query)
    return_vals["FundsHoldsCompaniesRelation"] = funds_hold_company_edge

    return return_vals


def display_spanner_query(spanner_query: str) -> None:
    """This function runs Graph Details  Query"""
    with st.expander("Spanner Query"):
        with stylable_container(
            "codeblock",
            """
            code {
                white-space: pre-wrap !important;
            }
            """,
        ):
            st.code(spanner_query, language="sql", line_numbers=False)
