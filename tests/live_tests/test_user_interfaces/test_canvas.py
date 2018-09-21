import pytest
from pydent.user_interfaces.designer import Canvas, CanvasException


def test_canvas_create(session):
    canvas = Canvas(session)
    canvas.create()
    print(canvas.plan.id)


def test_raises_exception_wiring_with_no_afts(session):
    canvas = Canvas(session)
    op1 = canvas.create_operation_by_name(
        "Make PCR Fragment", category="Cloning")
    op2 = canvas.create_operation_by_name("Check Plate", category="Cloning")

    with pytest.raises(CanvasException):
        canvas._set_wire(op1.outputs[0], op2.inputs[0])


def test_add_wire(session):
    canvas = Canvas(session)
    assert len(canvas.plan.wires) == 0
    op1 = canvas.create_operation_by_name(
        "Make PCR Fragment", category="Cloning")
    op2 = canvas.create_operation_by_name(
        "Rehydrate Primer", category="Cloning")

    canvas.add_wire(op2.outputs[0], op1.input("Forward Primer"))
    assert len(canvas.plan.wires) == 1
    wire = canvas.plan.wires[0]
    assert wire.source.allowable_field_type.sample_type_id == wire.destination.allowable_field_type.sample_type_id
    assert wire.source.allowable_field_type.object_type_id == wire.destination.allowable_field_type.object_type_id


def test_add_wire_sets_sample_from_destination(session):
    canvas = Canvas(session)
    assert len(canvas.plan.wires) == 0
    p = canvas.session.SampleType.find_by_name("Primer").samples[0]
    destination = canvas.create_operation_by_name(
        "Make PCR Fragment", category="Cloning")
    source = canvas.create_operation_by_name(
        "Rehydrate Primer", category="Cloning")
    canvas.set_field_value(destination.input("Forward Primer"), sample=p)
    canvas.add_wire(source.outputs[0], destination.input("Forward Primer"))
    assert source.outputs[0].sample == p


def test_add_wire_sets_sample_from_source(session):
    canvas = Canvas(session)
    assert len(canvas.plan.wires) == 0
    p = canvas.session.SampleType.find_by_name("Primer").samples[0]
    destination = canvas.create_operation_by_name(
        "Make PCR Fragment", category="Cloning")
    source = canvas.create_operation_by_name(
        "Rehydrate Primer", category="Cloning")
    canvas.set_field_value(source.outputs[0], sample=p)
    canvas.add_wire(source.outputs[0], destination.input("Forward Primer"))
    assert destination.input("Forward Primer").sample == p


def test_collect_matching_afts(session):
    canvas = Canvas(session)

    op1 = canvas.create_operation_by_name("Check Plate", category="Cloning")
    op2 = canvas.create_operation_by_name("E Coli Lysate", category="Cloning")
    afts = canvas._collect_matching_afts(op1, op2)
    print(afts)


def test_raise_exception_if_wiring_two_inputs(session):
    canvas = Canvas(session)
    assert len(canvas.plan.wires) == 0

    op1 = canvas.create_operation_by_name("Check Plate", category="Cloning")
    op2 = canvas.create_operation_by_name("Check Plate", category="Cloning")

    with pytest.raises(CanvasException):
        canvas.add_wire(op1.inputs[0], op2.inputs[0])


def test_raise_exception_if_wiring_two_outputs(session):
    canvas = Canvas(session)
    assert len(canvas.plan.wires) == 0

    op1 = canvas.create_operation_by_name("Check Plate", category="Cloning")
    op2 = canvas.create_operation_by_name("Check Plate", category="Cloning")

    with pytest.raises(CanvasException):
        canvas.add_wire(op1.outputs[0], op2.outputs[0])


def test_canvas_add_op(session):

    canvas = Canvas(session)
    canvas.create_operation_by_name("Yeast Transformation")
    canvas.create_operation_by_name("Yeast Antibiotic Plating")
    canvas.quick_wire_by_name("Yeast Transformation",
                              "Yeast Antibiotic Plating")
    canvas.create()

    p = session.Plan.find(canvas.plan.id)
    pass


def test_canvas_quick_create_chain(session):
    canvas = Canvas(session)

    canvas.quick_create_chain("Yeast Transformation",
                              "Check Yeast Plate",
                              "Yeast Overnight Suspension")
    assert len(canvas.plan.operations) == 3
    assert len(canvas.plan.wires) == 2


def test_chain_run_gel(session):
    canvas = Canvas(session)
    canvas.quick_create_chain(
        "Make PCR Fragment", "Run Gel", category="Cloning")


def test_quick_chain_to_existing_operation(session):
    canvas = Canvas(session)
    op = canvas.create_operation_by_name("Yeast Transformation")
    canvas.quick_create_chain(op, "Check Yeast Plate")
    assert len(canvas.plan.wires) == 1


def test_canvas_chaining(session):
    canvas = Canvas(session)
    ops = canvas.quick_create_chain("Assemble Plasmid", "Transform Cells",
                                    "Plate Transformed Cells", "Check Plate",
                                    category="Cloning")
    assert len(canvas.plan.wires) == 3
    new_ops = []
    for i in range(3):
        new_ops += canvas.quick_create_chain(
            ops[-1], ("E Coli Lysate", "Cloning"), "E Coli Colony PCR")[1:]
    assert len(canvas.plan.wires) == 2 * 3 + 3


def test_layout_edges_and_nodes(session):
    canvas = Canvas(session)
    canvas.quick_create_chain("Yeast Transformation",
                              "Check Yeast Plate", "Yeast Overnight Suspension")
    G = canvas.layout.G
    edges = list(G.edges)
    assert len(edges) == 2, "There should only be 2 edges/wires in the graph/plan"
    assert len(
        G.nodes) == 3, "There should only be 3 nodes/Operations in the graph/plan"
    assert edges[0][1] == edges[1][0], "Check Yeast Plate should be in both wires"


def test_load_canvas(session):

    canvas = Canvas(session, plan_id=122133)
    assert canvas is not None
    assert canvas.plan is not None
    assert canvas.plan.operations is not None

    # # data = canvas.plan.to_save_json()
    #
    # op = canvas.get_operation(113772)
    #
    # op2 = canvas.create_operation_by_name("Fragment Analyzing")
    # # canvas.quick_wire_ops(op, op2)
    # # data = canvas.plan.to_save_json()
    # # import json
    # # with open('temp.json', 'w') as f:
    # #     json.dump(data, f)
    # canvas.save()

    # for op in canvas.plan.operations:

    # for n in list(nx.topological_sort(G))[::-1]:
    #     op = G.nodes[n]['operation']
    #     op.y = y
    #     y += 75
    # canvas.save()

    # canvas.draw()/
    # print(canvas.url)