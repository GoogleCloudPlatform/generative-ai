import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import pandas as pd
import streamlit as st
import random
from database import *


def simple_func_nonx():
    graph = Network("900px", "900px", notebook=True, heading="")
    returnVals = graph_dtls_query()
    companies = returnVals.get("Companies")
    for index, row in companies.iterrows():
        graph.add_node(
            str(row["CompanySeq"]),
            label=row["name"],
            title=row["name"],
            shape="triangle",
        )

    sectors = returnVals.get("Sectors")
    for index, row in sectors.iterrows():
        graph.add_node(
            str(row["SectorSeq"]),
            label=row["sector_name"],
            shape="square",
            color="red",
            title=row["sector_name"],
        )


    # managers = returnVals.get("Managers")
    # for index, row in managers.iterrows():
    #     print(f"Index: {index}, Name: {row['name']}")
    #     graph.add_node(str(row['ManagerSeq']), label=row['name'],  color="green" , title=row['name'])

    funds = returnVals.get("Funds")
    for index, row in funds.iterrows():
        graph.add_node(
            str(row["NewMFSequence"]),
            label=row["fund_name"],
            color="green",
            title=row["fund_name"],
        )

    compSectorRelation = returnVals.get("CompanySectorRelation")
    for index, row in compSectorRelation.iterrows():
        graph.add_edge(str(row["CompanySeq"]), str(row["SectorSeq"]), title="BELONGS")

    # mgrFundRelation = returnVals.get("ManagerFundRelation")
    # for index, row in mgrFundRelation.iterrows():
    #      # print(f"Index: {index}, Company: {row['CompanySeq']}")
    #     graph.add_edge(str(row['NewMFSequence']), str(row['ManagerSeq']), title="MANAGES")
    # graph.add_edge('269371552712097792', '576460752303423488', title="BELONGS")

    fundHoldCompanyRelation = returnVals.get("FundsHoldsCompaniesRelation")
    for index, row in fundHoldCompanyRelation.iterrows():
        graph.add_edge(str(row["NewMFSequence"]), str(row["CompanySeq"]), title="HOLDS")
    
    # Add Legend Nodes
 
    
    
    
    graph.show("Anirban.html")
