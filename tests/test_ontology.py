import warnings
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace

ONTOLOGY_DIR = Path(__file__).parents[1] / "ontology"
ONTOLOGY_PATH = ONTOLOGY_DIR / "problem-bank.ttl"
SHAPES_PATH = ONTOLOGY_DIR / "shapes.ttl"
EXAMPLE_PATH = ONTOLOGY_DIR / "examples" / "information-processing-engineer.ttl"
FUSEKI_CONFIG_PATH = Path(__file__).parents[1] / "docker" / "fuseki" / "config.ttl"

PB = Namespace("https://belight2.github.io/problem_bank/ontology#")
PBR = Namespace("https://belight2.github.io/problem_bank/resource/")


def load_example_graph() -> Graph:
    graph = Graph()
    graph.parse(ONTOLOGY_PATH, format="turtle")
    graph.parse(EXAMPLE_PATH, format="turtle")
    return graph


def validate_graph(graph: Graph) -> tuple[bool, Graph, str]:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            module=r"rdflib\..*",
        )
        conforms, report_graph, report_text = validate(
            graph,
            shacl_graph=str(SHAPES_PATH),
            advanced=True,
        )
    return bool(conforms), report_graph, str(report_text)


def test_all_ontology_turtle_files_are_valid() -> None:
    for path in ONTOLOGY_DIR.rglob("*.ttl"):
        Graph().parse(path, format="turtle")


def test_fuseki_assembler_config_is_valid_turtle() -> None:
    Graph().parse(FUSEKI_CONFIG_PATH, format="turtle")


def test_information_processing_example_conforms_to_shapes() -> None:
    conforms, _, report = validate_graph(load_example_graph())

    assert conforms, str(report)


def test_prerequisite_cycle_is_rejected() -> None:
    graph = load_example_graph()
    graph.add(
        (
            PBR["concept-third-normal-form"],
            PB.prerequisiteOf,
            PBR["concept-functional-dependency"],
        )
    )

    conforms, _, report = validate_graph(graph)

    assert not conforms
    assert "선수 개념 관계" in str(report)
