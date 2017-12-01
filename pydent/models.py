"""Aquarium models

This module contains a set of classes for various various Aquarium objects. Trident models
inherit the Base class and have a model schema (handled by '@add_schema`) that handles
the JSON loading and dumping.

By default, Trident models capture ALL JSON attribute/values and sets the attributes to the
resultant object.

.. code-block:: python

    u = User.load({"id": 1, "login": "John"})
    u.login    # => "John"
    u.id       # => 1

Fields and field options are added as class variables in the model class definition.
Below lists various field options and their default values.

.. code-block:: python

        load_all = True     # load missing data attributes not explicitly defined during serialization
        strict = True       # throw error during marshalling instead of storing error
        include = {}        # fields to include for serialization/deserialization.
        additional = ()     # explicitly defined fields for serialization/deserialization.
        ignore = ()         # fields to filter during deserialization. These fields will be filtered from the JSON.
        load_only = ()      # fields to ignore during serialization
        dump_only = ()      # fields to ignore during deserialization

Trident models can also have nested relationships (for example, a Sample my possess a single SampleType while
a SampleType may possess several Samples). These relationships can be specified in the class definition along
with the field options above as in:

.. code-block:: python

    @add_schema
    class SampleType(Base):
        samples = fields.Nested("Sample", many=True)

In many cases, the model contains only a reference to the nested relationship, in this case, special fields
One and Many may be used to define this relationship. When called as an attribute, Trident will automatically
use the session connection with Aquarium to retrieve the given model.

For example, the following will define that SampleType has many Samples. When .samples is called on a
SampleType instance, Trident will use the database to retrieve all samples that have a sample_type_id
equal to the id of the SampleType:

.. code-block:: python

    @add_schema
    class SampleType(Base):
        samples = Many("Sample", params={"sample_type_id": lambda self: self.id})
"""

import warnings

import requests
from pydent.base import ModelBase
from pydent.exceptions import AquariumModelError
from pydent.marshaller import add_schema, fields
from pydent.relationships import One, Many, HasOne, HasMany, HasManyThrough, HasManyGeneric
from pydent.utils import magiclist, filter_list

__all__ = [
    "Account",
    "AllowableFieldType",
    "Budget",
    "Code",
    "Collection",
    "DataAssociation",
    "FieldType",
    "FieldValue",
    "Group",
    "Invoice",
    "Item",
    "Job",
    "JobAssociation",
    "Library",
    "Membership",
    "ObjectType",
    "Operation",
    "OperationType",
    "Plan",
    "PlanAssociation",
    "Sample",
    "SampleType",
    "Upload",
    "User",
    "UserBudgetAssociation",
    "Wire"
]


##### Mixins #####

class HasCode(object):
    """Access to latest code for OperationType, Library, etc."""

    def code(self, name):
        codes = [c for c in self.codes if c.name == name]
        codes = [c for c in codes if not hasattr(c, "child_id") or c.child_id is None]
        return codes[-1]


class FieldMixin(object):
    """Mixin for finding FieldType and FieldValue relationships"""

    def find_field_parent(self, model_name, id):
        """Callback for finding operation_type or sample_type. If parent_class does not match
        the expected nested model name (OperationType or SampleType), callback will return
        None"""
        if model_name == self.parent_class:
            # weird, but helps with refactoring this mixin
            fxn_name = ModelBase.find_using_session.__name__
            fxn = getattr(self, fxn_name)
            return fxn(model_name, id)


##### Models #####

@add_schema
class Account(ModelBase):
    """An Account model"""


@add_schema
class AllowableFieldType(ModelBase):
    """A AllowableFieldType model"""
    fields = dict(
        field_type=HasOne("FieldType"),
        object_type=HasOne("ObjectType"),
        sample_type=HasOne("SampleType")
    )


@add_schema
class Budget(ModelBase):
    """A Budget model"""
    fields = dict(
        user_budget_associations=HasMany("UserBudgetAssociation", "Budget")
    )


@add_schema
class Code(ModelBase):
    """A Code model"""
    fields = dict(
        user=HasOne("User")
    )

    # TODO: this is weird?
    def update(self):
        # TODO: make server side controller for code objects
        # since they may not always be tied to specific parent
        # controllers
        self.session.utils.update_code(self)


@add_schema
class Collection(ModelBase):  # pylint: disable=too-few-public-methods
    """A Collection model"""
    fields = dict(
        object_type=HasOne("ObjectType"),
        data_associations=HasManyGeneric("DataAssociation")
    )


@add_schema
class DataAssociation(ModelBase):
    """A DataAssociation model"""
    fields = dict(
        object=fields.JSON(),
        upload=HasOne("Upload")
    )

    @property
    def value(self):
        return self.object.get(self.key, None)


@add_schema
class FieldType(ModelBase, FieldMixin):
    """A FieldType model"""
    fields = dict(
        allowable_field_types=HasMany("AllowableFieldType", "FieldType"),
        operation_type=HasOne("OperationType", callback="find_field_parent", ref="parent_id"),
        sample_type=HasOne("SampleType", callback="find_field_parent", ref="parent_id")
    )

    @property
    def is_parameter(self):
        return self.ftype != "sample"

    def initialize_field_value(self, field_value=None):
        """
        Updates or initializes a new :class:`FieldValue` from this FieldType

        :param field_value: optional FieldValue to update with this FieldType
        :type field_value: FieldValue
        :return: updated FieldValue
        :rtype: FieldValue
        """

        if not field_value:
            field_value = FieldValue(name=self.name, role=self.role, field_type=self)
        if self.allowable_field_types:
            field_value.allowable_field_type_id = self.allowable_field_types[0].id
            field_value.allowable_field_type = self.allowable_field_types[0]
        return field_value


@add_schema
class FieldValue(ModelBase, FieldMixin):
    """A FieldValue model. One of the more complex models."""
    fields = dict(
        # FieldValue relationships
        field_type=HasOne("FieldType"),
        allowable_field_type=HasOne("AllowableFieldType"),
        item=HasOne("Item", ref="child_item_id"),
        sample=HasOne("Sample", ref="child_sample_id"),
        operation=HasOne("Operation", callback="find_field_parent", ref="parent_id"),
        parent_sample=One("Sample", callback="find_field_parent", ref="parent_id"),
        ignore=("object_type",)
    )

    def __init__(self, name=None, role=None, parent_class=None, parent_id=None,
                 field_type=None,
                 sample=None, value=None, item=None, container=None):
        """

        :param value:
        :type value:
        :param sample:
        :type sample:
        :param container:
        :type container:
        :param item:
        :type item:
        """
        self.column = None
        self.row = None
        self.role = role
        self.id = None
        self.name = name

        self.parent_class = parent_class
        self.parent_id = parent_id
        self.operation = None  # only if parent_class == "Operation"
        self.parent_sample = None  # only if parent_class == "Sample"

        self.sample = None
        self.child_sample_id = None

        self.item = None
        self.child_item_id = None

        self.field_type = None
        self.field_type_id = None

        self.allowable_field_type = None
        self.allowable_field_type_id = None

        self.value = None
        self.sample = None
        self.item = None
        self.container = None
        self.object_type = None  # object_type is not included in the deserialization/serialization

        if field_type:
            self.set_field_type(field_type)

        if any([value, sample, item, container]):
            self._set_helper(value=value, sample=sample, item=item, container=container)
        super().__init__(**vars(self))

    def show(self, pre=""):
        if self.sample:
            if self.child_item_id:
                item = " item: {}".format(self.child_item_id) + \
                       " in {}".format(self.item.object_type.name)
            else:
                item = ""
            print('{}{}.{}:{}{}'.format(pre, self.role, self.name, self.sample.name, item))
        elif self.value:
            print('{}{}.{}:{}'.format(pre, self.role, self.name, self.value))

    def _set_helper(self, value=None, sample=None, container=None, item=None):
        if item and container and item.object_type_id != container.id:
            raise AquariumModelError("Item {} is not in container {}".format(item.id, str(container)))
        if value:
            self.value = value
        if item:
            self.item = item
            self.child_item_id = item.id
            self.object_type = item.object_type
        if sample:
            self.sample = sample
            self.child_sample_id = sample.id
        if container:
            self.object_type = container

    def set_value(self, value=None, sample=None, container=None, item=None):
        self._set_helper(value=value, sample=sample, container=container, item=item)
        afts = self.field_type.allowable_field_types
        if self.sample:
            afts = filter_list(afts, sample_type_id=self.sample.sample_type_id)
        if self.object_type:
            afts = filter_list(afts, object_type_id=self.object_type.id)
        if len(afts) > 1:
            warnings.warn("More than one AllowableFieldType found that matches {}".format(
                self.dump(only=('name', 'role', 'id'), partial=True)))
        elif len(afts) == 1:
            self.set_allowable_field_type(afts[0])
        else:
            raise AquariumModelError("No allowable field type found for {} {}".format(self.role, self.name))
        return self

    def set_operation(self, op):
        self.parent_class = "Operation"
        self.parent_id = op.id
        self.operation = op

    def set_field_type(self, ft):
        """Sets properties from a field_type"""
        self.field_type = ft
        self.field_type_id = ft.id

    def set_allowable_field_type(self, allowable_field_type):
        self.allowable_field_type = allowable_field_type
        self.allowable_field_type_id = allowable_field_type.id

    def choose_item(self, first=True):
        """Set the item associated with the field value"""
        index = 0
        if not first:
            index = -1
        items = self.compatible_items()
        if len(items) > 0:
            item = items[index]
            self.set_value(item=item)
            return item
        return None

    def compatible_items(self):
        """Find items compatible with the field value"""
        return self.session.utils.compatible_items(self.sample.id, self.allowable_field_type.object_type_id)


@add_schema
class Group(ModelBase):
    """A Group model"""
    pass


@add_schema
class Invoice(ModelBase):
    """A Invoice model"""
    pass


@add_schema
class Item(ModelBase):
    """A Item model"""
    fields = dict(
        sample=HasOne("Sample"),
        object_type=HasOne("ObjectType"),
        data_associations=HasManyGeneric("DataAssociation"),
        data=fields.JSON(allow_none=True)
    )


@add_schema
class Job(ModelBase):
    """A Job model"""
    fields = dict(
        job_associations=HasMany("JobAssociation", "Job"),
        operations=HasManyThrough("Operation", "JobAssociation")
    )


@add_schema
class JobAssociation(ModelBase):
    """A JobAssociation model"""
    fields = dict(
        job=HasOne("Job"),
        operation=HasOne("Operation")
    )


@add_schema
class Library(ModelBase, HasCode):
    """A Library model"""
    fields = dict(
        codes=HasManyGeneric("Code")
    )


@add_schema
class Membership(ModelBase):
    fields = dict(
        user=HasOne("User"),
        group=HasOne("Group")
    )


@add_schema
class ObjectType(ModelBase):
    """A ObjectType model"""


@add_schema
class Operation(ModelBase):
    """A Operation model"""
    fields = dict(
        field_values=HasManyGeneric("FieldValue"),
        data_associations=HasManyGeneric("DataAssociation"),
        operation_type=HasOne("OperationType"),
        job_associations=HasMany("JobAssociation", "Operation"),
        jobs=HasManyThrough("Job", "JobAssociation"),
        plan_associations=HasMany("PlanAssociation", "Operation"),
        plans=HasManyThrough("Plan", "PlanAssociation")
    )

    # @staticmethod
    # def next_position():
    #     X += 176
    #     if X > 800:
    #         X = 0
    #         Y += 6
    #     return [X, Y]

    def init_field_values(self):
        """Inialize the field values form the field types of the parent operation type"""
        for field_type in self.operation_type.field_types:
            self.set_field_value(field_type.name, field_type.role)
            # self.show()

    def field_value(self, name, role):
        """Returns :class:`FieldValue` with name and role. Return None if not found."""
        if self.field_values:
            fvs = filter_list(self.field_values, name=name, role=role)
            if fvs[0].field_type.array:
                return fvs
            elif len(fvs) > 1:
                raise AquariumModelError(
                    "More than one FieldValue found for the non-array field value of operation {}(id={}).{}.{}".format(
                        self.operation_type.name, self.id, role, name))
            elif len(fvs) == 1:
                return fvs[0]

    def set_field_value(self, name, role, sample=None, item=None, value=None, container=None):
        """Sets the value of a :class:`FieldValue`. If the FieldValue does not exist,
        an 'empty' FieldValue will be created from the field_type"""
        # get the field value
        fv = self.field_value(name, role)

        # get the field type
        ft = self.operation_type.field_type(name, role)
        if not ft:
            AquariumModelError("No FieldType found for OperationType {}.{}.{}".format(
                self.operation_type.name, role, name))

        # initialize the field value from the field type
        if not fv:
            fv = ft.initialize_field_value(fv)

        # update the field_value with this operation
        fv.set_operation(self)

        # set the value, finds allowable_field_types, etc.
        fv.set_value(value=value, sample=sample, item=item, container=container)
        return self

    def set_field_type(self, field_value):
        """Sets the :class:`FieldType` associated with a given :class:`FieldValue`"""
        field_types = filter_list(self.operation_type.field_types, **field_value.dump(only=('name', 'role')))
        if field_types:
            return field_types[-1]
        else:
            raise AquariumModelError(
                "Could not find field type of {} named {} in operation_type {}".format(
                    field_value.role, field_value.name, self.operation_type.name))

    @property
    def plan(self):
        return self.plans[0]

    @property
    @magiclist
    def inputs(self):
        return [fv for fv in self.field_values if fv.role == 'input']

    @property
    @magiclist
    def outputs(self):
        return [fv for fv in self.field_values if fv.role == 'output']


@add_schema
class OperationType(ModelBase, HasCode):
    """A OperationType model"""
    fields = dict(
        operations=HasMany("Operation", "OperationType"),
        field_types=HasManyGeneric("FieldType"),
        codes=HasManyGeneric("Code")
    )

    def instance(self):
        pass

    def field_type(self, name, role):
        if self.field_types:
            fts = filter_list(self.field_types, role=role, name=name)
            if fts:
                return fts[0]


@add_schema
class Plan(ModelBase):
    """A Plan model"""
    fields = dict(
        data_associations=HasManyGeneric("DataAssociation"),
        plan_associations=HasMany("PlanAssociation", "Plan"),
        operations=HasManyThrough("Operation", "PlanAssociation")
    )

    def __init__(self):
        self.id = None
        self.name = None
        self.status = "planning"
        self.layout = {"id": 0, "parent_id": -1, "wires": [], "name": "no_name"}
        self.operations = []
        self.source = None
        self.destination = None
        super().__init__()

    def callback(self):
        pass

    def add_operations(self, ops):
        self.operations = ops

    def wire(self, src, dest):
        self.source = src
        self.destination = dest

    def add_wires(self, pairs):
        for src, dest in pairs:
            self.wire(src, dest)

    def submit(self, user, budget):
        self.session.create.create_plan(self, user, budget)


@add_schema
class PlanAssociation(ModelBase):
    """A PlanAssociation model"""
    fields = dict(
        plan=HasOne("Plan"),
        operation=HasOne("Operation")
    )


@add_schema
class Sample(ModelBase):
    """A Sample model"""
    fields = dict(
        # sample relationships
        sample_type=HasOne("SampleType"),
        items=HasMany("Item", ref="sample_id"),
        field_values=HasMany("FieldValue", ref="parent_id"),
    )

    def __init__(self, name=None, project=None, sample_type_id=None):
        self.name = name
        self.project = project
        self.sample_type_id = sample_type_id
        super().__init__(**vars(self))

    @property
    def identifier(self):
        """Return the identifier used by Aquarium in autocompletes"""
        return "{}: {}".format(self.id, self.name)

    def field_value(self, name):
        for field_value in self.field_values:
            if field_value.name == name:
                return field_value
        return None

    @property
    def field_names(self):
        return [fv.name for fv in self.field_values]


@add_schema
class SampleType(ModelBase):
    """A SampleType model"""
    fields = dict(
        samples=HasMany("Sample", "SampleType"),
        field_types=Many("FieldType",
                         params=lambda self: {"parent_id": self.id, "parent_class": self.__class__.__name__})
    )

    def create(self):
        return self.session.create.create_samples([self])


@add_schema
class Upload(ModelBase):
    """An Upload model"""

    @property
    def temp_url(self):
        return self.session.Upload.where_using_session({"id", self.id}, {"methods": ["url"]})[0].url

    @property
    def data(self):
        result = requests.get(self.temp_url)
        return result.content


@add_schema
class User(ModelBase):
    """A User model"""
    fields = dict(
        groups=HasMany("Group", "User"),
        additional=("name", "id", "login"),
        ignore=("password_digest", "remember_token", "key")
    )


@add_schema
class UserBudgetAssociation(ModelBase):
    """An association model between a User and a Budget"""
    fields = dict(
        budget=HasOne("Budget"),
        user=HasOne("User")
    )


@add_schema
class Wire(ModelBase):
    """A Wire model"""
    fields = dict(
        # load_only=False, will force dumping of FieldValues here...
        source=HasOne("FieldValue", ref="from_id", dump_to="from", load_only=False),
        destination=HasOne("FieldValue", ref="to_id", dump_to="to", load_only=False)
    )

    def show(self, pre=""):
        """Show the wire nicely"""
        print(pre + self.source.operation.operation_type.name +
              ":" + self.source.name +
              " --> " + self.destination.operation.operation_type.name +
              ":" + self.destination.name)
