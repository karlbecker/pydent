"""Test for pydent.relationships.py."""
from pydent import ModelBase
from pydent.relationships import HasMany
from pydent.relationships import HasManyGeneric
from pydent.relationships import HasManyThrough
from pydent.relationships import HasOne
from pydent.relationships import Many
from pydent.relationships import One


def test_one():
    """Tests the One relationship.

    The relationship holds a callback function_name and a set of
    parameters. Callback should default to 'find'
    """

    # default attributes
    one = One("ModelName")
    assert one.nested == "ModelName"
    assert one.callback == ModelBase.find_callback.__name__
    assert one.many is False

    # basic attributes
    one = One("ModelName", callback="mycallback", callback_args=(1, 2, 3))
    assert one.nested == "ModelName"
    assert one.callback == "mycallback"
    assert one.callback_args == ("ModelName", 1, 2, 3)
    assert not one.many


def test_many():
    """Tests the Many relationship.

    The relationship holds a callback function_name and a set of
    parameters. Callback should default to 'where'
    """

    # basic attributes
    many = Many("ModelName", callback="mycallback", callback_args=(1, 2, 3))
    assert many.nested == "ModelName"
    assert many.callback == "mycallback"
    assert many.callback_args == ("ModelName", 1, 2, 3)
    assert many.many

    # default attributes
    many2 = Many("ModelName")
    assert many2.callback == ModelBase.where_callback.__name__


def test_has_many():
    """
    Tests the HasMany relationship. Its expected with a MyModel and
    RefModelName, that the params should return a lambda callable equiavalent
    to:

    .. code-block:: python

        params = lambda: x: {"ref_model_id": x.id}

    """

    class RefModel:
        id = 4
        name = "myname"

    # has_many tries to return lambda x: {"ref_model_id": x.id}
    hasmany = HasMany("ModelName", RefModel.__name__)
    assert hasmany.nested == "ModelName"
    assert hasmany.callback_args[1](RefModel) == {"ref_model_id": 4}

    # has_many tries to return lambda x: {"ref_model_name": x.name}
    hasmany = HasMany("ModelName", RefModel.__name__, attr="name")
    assert hasmany.callback_args[1](RefModel) == {"ref_model_name": "myname"}


def test_has_one():
    """Tests the HasOne relationship. Its expected that with MyModel, that the
    returned params should be:

    .. code-block:: python

        params = lambda x: x.my_model_id
    """

    class MyModel:
        my_model_id = 4
        my_model_name = "myname"

    # has_many tries to return lambda x: x.my_model_id
    hasone = HasOne("MyModel")
    assert hasone.nested == "MyModel"
    assert hasone.callback_args[1](MyModel) == 4

    # has_many tries to return lambda x: x.my_model_name
    hasone = HasOne("MyModel", attr="name")
    assert hasone.callback_args[1](MyModel) == "myname"


def test_has_one_with_ref():
    """Tests the HasOne relationship. Its expected that with MyModel, that the
    returned params should be:

    .. code-block:: python

        params = lambda x: x.my_model_id
    """

    class MyModel:
        parent_id = 4
        my_model_name = "myname"

    # tries to return lambda x: x.my_model_id
    hasone = HasOne("MyModel", ref="parent_id")
    assert hasone.ref == "parent_id"
    assert hasone.nested == "MyModel"
    assert hasone.callback_args[1](MyModel) == 4


def test_has_many_generic():
    """Tests the HasManyGeneric relationship. Its expected that with MyModel,
    that the returned params should be:

    .. code-block:: python

        params = lambda x: {"parent_id": x.id}
    """

    class MyModel:
        pass

    mymodel = MyModel()
    mymodel.id = 4

    hasmanygeneric = HasManyGeneric("MyModel")
    assert hasmanygeneric.nested == "MyModel"

    def expected_fxn(model):
        return {"parent_id": model.id}

    fxn = hasmanygeneric.callback_args[1]
    assert expected_fxn(mymodel) == fxn(mymodel)
    assert fxn(mymodel) == {"parent_id": 4}


def test_has_many_through():
    """Tests the HasManyThrough relationship. This is a little more complicated
    than the other relationships, but its expected that with MyModel and
    ThroughModel that the returned params should be:

    .. code-block:: python

        params = lambda x: {"id": [m.my_model_id for m in x.through_models]}


    For example, if a User has many Budgets through a BudgetAssociation then
    basically the user instance will be passed to the lambda and so the
    relationship will attempt to find models based on the following:

    .. code-block:: python

        # gather budget_ids from user's budget_associations
        params = lambda user: {
            "id": [m.budget_id for m in user.budget_associations]}

    When user.budgets is called, whats really happening is that user instance
    is fullfilling the HasManyThrough relationship by finding the budget_ids
    from the user instance's budget_associations.
    The equivalent code for this is:

    .. code-block:: python

        budget_ids = [m.budget_id for m in user.budget_associations]
        budgets = user.where("Budget", {"id": budget_ids})
    """

    class ThisModel:
        pass

    class ThroughModel:
        pass

    this_model = ThisModel()
    through_model = ThroughModel()
    through_model.my_model_id = 4
    this_model.through_models = [through_model]

    hasmanythrough = HasManyThrough("MyModel", "ThroughModel")
    assert hasmanythrough.nested == "MyModel"

    def expected_fxn(model):
        return {"id": [x.my_model_id for x in model.through_models]}

    fxn = hasmanythrough.callback_args[1]
    assert fxn(this_model) == expected_fxn(this_model)
    assert fxn(this_model) == {"id": [4]}
