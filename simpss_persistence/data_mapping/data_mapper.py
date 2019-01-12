"""Map between the data from the Kafka consumer to the Cassandra db."""


def convert(source, name_map):
    """
    Convert the source message to a destination message,
    using the key mapping defined in name_map.

    Parameters
    ----------
    source: Dict[str, Any]
        the source message

    name_map: Dict[str, str]
        mapping of the key names from the source to the destination message

    Returns
    -------
    Dict[str, Any]
        the converted message, contains the same values as the source message
        but associated with the new keys.
    """
    if len(source) != len(name_map):
        raise ValueError(
            "Source message and name mapping should have the same length, got {} and {} instead"
            .format(len(source), len(name_map)))

    converted = {
        k_dest: source[k_source]
        for k_source, k_dest in name_map.items()
    }
    return converted
