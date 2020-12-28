from copy import deepcopy
import src.utils
from src import Commons
commons = Commons


def function_arg_parser(source_parser, name, args=None,
                        kwargs=None, **other_confs):
    """
    Parses the function, returns a function that requires:
        + local namespace
        + *args
        + **kwargs

    And returns the value

    The function is a string evaluated at runtime in the
    context of the instance. Therefore it can be a method
    like `self.method` or a third function in Commons like
    `commons.function`
    """

    # print("Parsing fun: ", name, args, kwargs, other_confs)
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    fun = deepcopy(name)
    args = deepcopy(args)
    kwargs = deepcopy(kwargs)

    args = [source_parser(i, True) for i in args]
    kwargs = {k: source_parser(v, True) for k, v in kwargs.items()}

    def return_fun(local, *n_args, **n_kwargs):
        # print("ret_fun_parse:", args)
        eff_args = [i(local, *n_args, **n_kwargs) for i in args]
        eff_kwargs = {k: v(local, *n_args, **n_kwargs) for k, v in kwargs.items()}

        eff_args = eff_args + list(n_args)
        eff_kwargs.update(n_kwargs)

        globs = globals()
        globs['Commons'] = src.Commons
        globs['commons'] = src.Commons

        f = eval(fun, globs, local)

        return f(*eff_args, **eff_kwargs)
    return return_fun


def attribute_arg_parser(source_parser, name, **other_confs):
    """
    Returns a function accepting a namespace, *args and **kwargs, ignores the ?args and
    returns the value

    As in the function case the name is evaluated at runtime in
    the context of the instance
    """
    def return_fun(local, *args, **kwargs):
        # print("Locals prima di trovare l'attributo: ", local)
        return eval(name, globals(), local)

    return return_fun


def kwarg_arg_parser(source_parser, name, dic_name="kwargs", **other_confs):
    def return_fun(local, *args, **kwargs):
        return local['kwargs'][name]
    return return_fun


def source_parse(configuration, in_source=False):
    """
    Takes the configuration parsed and desugared by other metaclasses
    and returns the actual objects dealing with retrieving and modifying data

    This function operates only on the subtrees of the configuration
    marked by a "source" dictionary key, the in_source flag allows recursive
    parsing of the configuration manipulating source nodes and leaving other
    untouched

    It returns a closure
    """
    # print("Parsing conf: ", configuration)
    if not in_source:
        if type(configuration) == list:
            return [source_parse(i, in_source) for i in configuration]

        if type(configuration) != dict:
            return configuration

        return {k: source_parse(v, k == 'source') for k, v in configuration.items()} # for each key it recurses but checks
                                                                                     # if the key is source and flags the
                                                                                     # call if that's the case

    if type(configuration) != dict:
        def simple_res(*args, **kwargs):
            return configuration
        return simple_res

    if 'source' in configuration:
        return source_parse(configuration['source'], in_source)

    """
    Here the configuration is parsed based on the type of source
        + fun: means the source of the data will be a function call
        + att: the source is an attribute of the instance
        + kwarg: the source is a keyword argument provided to the call
    
    `parsed` is a callable object which will return the data
    """
    t = configuration['type']
    if t == 'fun':
        parsed = function_arg_parser(source_parse, **configuration)
    elif t == 'att':
        parsed = attribute_arg_parser(source_parse, **configuration)
    elif t == 'kwarg':
        parsed = kwarg_arg_parser(source_parse, **configuration)
    else:
        raise AttributeError('Neither function nor attribute')

    """
    The data is going to be in the format of a pandas dataframe,
    here we provide utilities to modify the columns to either rename
    them or select only ones we're interested in
    
    rename is a dictionary accepted by Pandas' rename method
    """
    columns = configuration.get('columns', [])
    columns, rename = src.utils.parse_columns(columns)
    rename.update(configuration.get('rename', {}))

    """
    How the retrieved data has to be stored
    Possible options:
        + None: the result is simply returned
        + `#var`: the result is stored as the attribute `var`
            of the instance
        + `$var.key`: the result is stored with key `key` in the
            dictionary `var` passed through local variable dictionary
        + `var`: the result is stored in the local variable `var`
            through the local variable dictionary
    """
    store_action = configuration.get('store', None)

    """
    Possible options:
        + NoForward: doesn't forward positional and keyword arguments
            to the lower steps
    """
    options = configuration.get('options', [])

    def function_returned(local, *args, **kwargs):
        """
        @param local: the local environment, allowing the definition
            of variables
        @param args: positional arguments
        @param kwargs: keyword arguments
        @return:

        """
        if 'NoForward' in options:
            args = []
            kwargs = {}
        r = parsed(local, *args, **kwargs)

        if len(columns) > 0:
            r = r[columns]

        if len(rename.keys()) > 0:
            r = r.rename(columns=rename)

        if store_action is None:
            pass
        elif store_action[0] == '#':
            setattr(local['self'], store_action[1:], r)
        elif store_action[0] == '$':
            d, k = tuple(store_action[1:].split('.')[:2])
            local[d][k] = r
        else:
            local[store_action] = r
        return r

    return function_returned
