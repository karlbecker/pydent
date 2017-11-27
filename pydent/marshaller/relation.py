from marshmallow.fields import Nested
import functools

class Relation(Nested):
    """Defines a nested relationship with another model. Is a subclass of :class:`Nested`.

    Uses "callback" with "params" to find models. Callback is
    applied to the model that is fullfilling this relation. Params may include lambdas
    of the form "lambda self: <do something with self>" which passes in the model
    instance.
    """

    def __init__(self, model, callback, params, *args, allow_none=True, **kwargs):
        """Relation initializer.

        :param model: target model
        :type model: basestring
        :param args: positional parameters
        :type args:
        :param callback: function to use in Base to find model
        :type callback: basestring or callable
        :param params: tuple or list of variables (or callables) to use to search for the model. If param is
        a callable, the model instance will be passed in.
        :type params: tuple or list
        :param kwargs: rest of the parameters
        :type kwargs:
        """
        # if kwargs.get("load_only", None) is None:
        #     kwargs["load_only"] = True  # note that "load_only" is important and prevents dumping of all relationships
        super().__init__(model, *args, allow_none=allow_none, **kwargs)
        self.callback = callback

        # force params to be an iterable
        if not isinstance(params, (list, tuple)):
            params = (params,)
        self.params = params

    def _serialize(self, nested_obj, attr, obj):
        dumped = None

        def dump(nobj):
            return nobj.dump(_depth=self.root._depth+1, dump_depth=self.root.dump_depth, dump_all_relations=True)

        if nested_obj:
            if isinstance(nested_obj, list):
                dumped = []
                for x in nested_obj:
                    xdumped = None
                    if x is not None:
                        xdumped = dump(x)
                    dumped.append(xdumped)
            else:
                dumped = dump(nested_obj)
        return dumped

    def __repr__(self):
        return "<{} (model={}, callback={}, params={})>".format(self.__class__.__name__,
                                                self.nested, self.callback, self.params)



