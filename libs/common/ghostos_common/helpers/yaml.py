def yaml_multiline_string_pipe(dumper, data):
    text_list = [line.rstrip() for line in data.splitlines()]
    fixed_data = "\n".join(text_list)
    if len(text_list) > 1:
        return dumper.represent_scalar('tag:yaml.org,2002:str', fixed_data, style="|")
    return dumper.represent_scalar('tag:yaml.org,2002:str', fixed_data)


def yaml_pretty_dump(data, dumper=None, **kwargs) -> str:
    from yaml.dumper import SafeDumper
    import yaml

    class PrettyDumper(SafeDumper):
        pass

    PrettyDumper.add_representer(str, yaml_multiline_string_pipe)

    if dumper is None:
        dumper = PrettyDumper
    if "allow_unicode" not in kwargs:
        kwargs["allow_unicode"] = True
    if "sort_keys" not in kwargs:
        kwargs["sort_keys"] = False
    return yaml.dump(data, Dumper=dumper, **kwargs)
