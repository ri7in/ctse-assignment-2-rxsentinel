"""Compose the four-agent pipeline as a LangGraph StateGraph.

Topology:

         (entry)
            |
            v
    coordinator_validate
       |          |
       v          v
   "halt"     "parser"
       |          |
       |          v
       |     med_parser
       |          |
       |          v
       |   interaction_analyzer
       |          |
       |          v
       |   patient_communicator
       |          |
       v          v
    coordinator_assemble
            |
            v
           END

State is a TypedDict (`RxState`); each node returns a partial dict that
LangGraph merges into the cumulative state before invoking the next node.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from rxsentinel.agents import (
    coordinator_assemble,
    coordinator_validate,
    interaction_analyzer,
    med_parser,
    patient_communicator,
)
from rxsentinel.agents.coordinator import should_continue
from rxsentinel.state import RxState


def build_graph():
    """Build and compile the LangGraph StateGraph for RxSentinel."""
    graph: StateGraph = StateGraph(RxState)

    graph.add_node("coordinator_validate", coordinator_validate)
    graph.add_node("med_parser", med_parser)
    graph.add_node("interaction_analyzer", interaction_analyzer)
    graph.add_node("patient_communicator", patient_communicator)
    graph.add_node("coordinator_assemble", coordinator_assemble)

    graph.set_entry_point("coordinator_validate")

    # Conditional edge: coordinator decides "proceed" or "halt".
    graph.add_conditional_edges(
        "coordinator_validate",
        should_continue,
        {
            "parser": "med_parser",
            "halt": "coordinator_assemble",
        },
    )

    # Linear pipeline through the workers.
    graph.add_edge("med_parser", "interaction_analyzer")
    graph.add_edge("interaction_analyzer", "patient_communicator")
    graph.add_edge("patient_communicator", "coordinator_assemble")

    graph.add_edge("coordinator_assemble", END)

    return graph.compile()
