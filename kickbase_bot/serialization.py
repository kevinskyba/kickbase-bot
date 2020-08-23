from kickbase_api.models.base_model import BaseModel


def _remove_blacklisted_iterative(obj):
    if not hasattr(obj, "keys"):
        obj = obj.__dict__
    if '_json_transform' in obj.keys():
        del obj['_json_transform']
    if '_json_mapping' in obj.keys():
        del obj['_json_mapping']
    for k, v in obj.items():
        if isinstance(v, list):
            obj[k] = [_remove_blacklisted_iterative(x) for x in v]
        if isinstance(v, dict):
            v = _remove_blacklisted_iterative(v)
            obj[k] = v
        if isinstance(v, BaseModel):
            v = v.__dict__
            v = _remove_blacklisted_iterative(v)
            obj[k] = v
    return obj


def _serialize(obj):
    d = obj.__dict__
    return _remove_blacklisted_iterative(d)
