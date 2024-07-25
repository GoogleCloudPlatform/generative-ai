from database import *
from pyvis.network import Network


def simple_func_nonx():
    """This function is for generating the Graph Visualization"""

    graph = Network("900px", "900px", notebook=True, heading="")
    return_vals = graph_dtls_query()
    companies = return_vals.get("Companies")
    for index, row in companies.iterrows():
        graph.add_node(
            str(row["CompanySeq"]),
            label=row["name"],
            title=row["name"],
            shape="triangle",
        )

    sectors = return_vals.get("Sectors")
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

    funds = return_vals.get("Funds")
    for index, row in funds.iterrows():
        graph.add_node(
            str(row["NewMFSequence"]),
            label=row["fund_name"],
            color="green",
            title=row["fund_name"],
        )

    comp_sector_relation = return_vals.get("CompanySectorRelation")
    for index, row in comp_sector_relation.iterrows():
        graph.add_edge(str(row["CompanySeq"]), str(row["SectorSeq"]), title="BELONGS")

    # mgrFundRelation = returnVals.get("ManagerFundRelation")
    # for index, row in mgrFundRelation.iterrows():
    #      # print(f"Index: {index}, Company: {row['CompanySeq']}")
    #     graph.add_edge(str(row['NewMFSequence']), str(row['ManagerSeq']), title="MANAGES")
    # graph.add_edge('269371552712097792', '576460752303423488', title="BELONGS")

    fund_hold_company_relation = return_vals.get("FundsHoldsCompaniesRelation")
    for index, row in fund_hold_company_relation.iterrows():
        graph.add_edge(str(row["NewMFSequence"]), str(row["CompanySeq"]), title="HOLDS")

    # Add Legend Nodes

    graph.show("graph_viz.html")
