"""This module is the page for Graph Viz Data Search feature"""

# pylint: disable=import-error, line-too-long, unused-variable

from database import graph_dtls_query
from pyvis.network import Network


def generate_graph() -> None:
    """This function is for generating the Graph Visualization"""

    graph = Network("900px", "900px", notebook=True, heading="")
    return_vals = graph_dtls_query()
    companies = return_vals.get("Companies")
    for index, row in companies.iterrows():  # type: ignore[union-attr]  # might ignore other potential errors
        graph.add_node(
            str(row["CompanySeq"]),
            label=row["name"],
            title=row["name"],
            shape="triangle",
        )

    sectors = return_vals.get("Sectors")
    for index, row in sectors.iterrows():  # type: ignore[union-attr]  # might ignore other potential errors
        graph.add_node(
            str(row["SectorSeq"]),
            label=row["sector_name"],
            shape="square",
            color="red",
            title=row["sector_name"],
        )

    funds = return_vals.get("Funds")
    for index, row in funds.iterrows():  # type: ignore[union-attr]  # might ignore other potential errors
        graph.add_node(
            str(row["NewMFSequence"]),
            label=row["fund_name"],
            color="green",
            title=row["fund_name"],
        )

    comp_sector_relation = return_vals.get("CompanySectorRelation")
    for index, row in comp_sector_relation.iterrows():  # type: ignore[union-attr]  # might ignore other potential errors
        graph.add_edge(str(row["CompanySeq"]), str(row["SectorSeq"]), title="BELONGS")

    fund_hold_company_relation = return_vals.get("FundsHoldsCompaniesRelation")
    for index, row in fund_hold_company_relation.iterrows():  # type: ignore[union-attr]  # might ignore other potential errors
        graph.add_edge(str(row["NewMFSequence"]), str(row["CompanySeq"]), title="HOLDS")

    graph.show("graph_viz.html")
